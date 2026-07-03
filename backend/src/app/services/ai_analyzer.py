"""AI分析サービス (Phase1: scikit-learn ベース)

直接 API から呼び出されるファサード。
保存済みモデルがない場合は統計ベースの簡易スコアを返す。
"""

from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.app.ml.features import (
    FEATURE_COLUMNS,
    build_label_theoretical,
    compute_basic_features,
    compute_context_features,
    compute_deviation_features,
)

DEFAULT_MODEL_PATH = "models/slot_model.pkl"


class SlotAIAnalyzer:
    """店舗データの分析・予測ファサード"""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        if Path(self.model_path).exists():
            from src.app.ml.model import SlotSettingModel

            self._model = SlotSettingModel.load(self.model_path)
        return self._model

    def analyze_store(
        self,
        store_data: dict,
        theoretical: dict | None = None,
        target_date: date | None = None,
    ) -> dict:
        """店舗の台データを分析して高設定候補を返す

        Args:
            store_data: {"machines": [...]}
            theoretical: {model_name: {"diff_rate_per_game": float, ...}}
            target_date: データ日付 (省略時は today)

        Returns:
            {
              "high_setting_probability": float,
              "confidence_score": float,
              "recommended_machines": [int, ...],
              "analysis_details": {...},
            }

        """
        machines = store_data.get("machines", [])
        if not machines:
            return {
                "high_setting_probability": 0.0,
                "confidence_score": 0.0,
                "recommended_machines": [],
                "analysis_details": {"error": "データが不足しています"},
            }

        if theoretical is None:
            theoretical = {}
        if target_date is None:
            target_date = datetime.now().date()

        df = pd.DataFrame(machines)
        df = compute_basic_features(df)
        df = compute_deviation_features(df, theoretical)
        df = compute_context_features(df, target_date)

        model = self._load_model()

        if model is not None:
            scores = model.predict_proba(df)
        else:
            # モデル未学習の場合: 差枚率ベースの簡易スコア
            scores = self._statistical_scores(df)

        # CLAUDE.md 実戦ルール: ゲーム数 <3000G は除外 (スコア半減)
        low_game_mask = df["games_played"].fillna(0) < 3000
        scores = scores.copy()
        scores[low_game_mask] *= 0.5

        df["_score"] = scores

        # 推奨台: スコア 0.7 以上、かつゲーム数 3000G 以上
        recommended = (
            df[
                (df["_score"] >= 0.7)
                & (df["games_played"].fillna(0) >= 3000)
            ]
            .sort_values("_score", ascending=False)
            .head(5)["machine_number"]
            .tolist()
        )

        # 全体の高設定確率 = 上位スコアの平均
        top_scores = sorted(scores, reverse=True)[:5]
        high_setting_prob = float(np.mean(top_scores)) if top_scores else 0.0

        # 信頼度: データ数とゲーム数に基づく
        confidence = min(1.0, len(machines) / 50)

        return {
            "high_setting_probability": high_setting_prob,
            "confidence_score": confidence,
            "recommended_machines": [int(m) for m in recommended],
            "analysis_details": {
                "total_machines": len(machines),
                "top_candidates": df.nlargest(5, "_score")[
                    ["machine_number", "model_name", "diff_rate", "_score"]
                ]
                .rename(columns={"_score": "score"})
                .to_dict("records"),
                "analysis_date": datetime.now().isoformat(),
                "model_used": "trained_model" if model else "statistical",
            },
        }

    def _statistical_scores(self, df: pd.DataFrame) -> np.ndarray:
        """モデル未学習時の統計ベーススコア"""
        diff_rate = df["diff_rate"].fillna(0)
        # 差枚率を [0, 1] に正規化 (最大 +3 枚/G 想定)
        scores = (diff_rate / 3.0).clip(0, 1).values
        return scores

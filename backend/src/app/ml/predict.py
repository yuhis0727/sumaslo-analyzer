"""予測スクリプト

保存済みモデルを使って台ごとの高設定スコアを算出し、
predictions テーブルに書き込む。
"""

from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from src.app.ml.features import (
    compute_basic_features,
    compute_context_features,
    compute_deviation_features,
    compute_timeseries_features,
)
from src.app.ml.model import SlotSettingModel
from src.app.ml.train import load_machines, load_theoretical_values
from src.app.models.slot_data import Machine, Prediction

DEFAULT_MODEL_PATH = "models/slot_model.pkl"


def predict_store(
    db: Session,
    store_id: int,
    target_date: date,
    model_path: str = DEFAULT_MODEL_PATH,
) -> list[dict]:
    """指定店舗・日付の台ごとに予測スコアを算出し DB に保存する

    Returns:
        予測結果のリスト (machine_number, prediction_score, predicted_setting, confidence)

    """
    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"モデルファイルが見つかりません: {model_path}\n"
            "先に train.py を実行してください。"
        )

    model = SlotSettingModel.load(model_path)
    theoretical = load_theoretical_values(db)

    # 当日データ
    day_rows = (
        db.query(Machine)
        .filter(Machine.store_id == store_id, Machine.date == target_date)
        .all()
    )
    if not day_rows:
        return []

    day_df = pd.DataFrame(
        [
            {
                "store_id": r.store_id,
                "machine_number": r.machine_number,
                "model_name": r.model_name,
                "date": r.date,
                "games_played": r.games_played,
                "diff_medals": r.diff_medals,
                "bonus_count": r.bonus_count,
                "reg_count": r.reg_count,
                "big_count": r.big_count,
                "at_count": r.at_count,
            }
            for r in day_rows
        ]
    )

    # 過去データ
    history_df = load_machines(db, store_id)
    history_df = history_df[history_df["date"] < target_date]

    # 特徴量計算
    day_df = compute_basic_features(day_df)
    day_df = compute_deviation_features(day_df, theoretical)
    day_df = compute_context_features(day_df, target_date)
    day_df = compute_timeseries_features(day_df, history_df)

    scores = model.predict_proba(day_df)
    settings = model.predict_setting(day_df)

    # ゲーム数が少ない台はスコアを下げる (CLAUDE.md 実戦ルール: <3000G は除外)
    low_game_mask = day_df["games_played"].fillna(0) < 3000
    scores[low_game_mask] = scores[low_game_mask] * 0.5

    # 信頼度: ゲーム数に基づく (多いほど高い)
    confidence = (day_df["games_played"].fillna(0).clip(0, 10000) / 10000).values

    results = []
    for i, row in day_df.iterrows():
        pred = Prediction(
            store_id=store_id,
            machine_number=int(row["machine_number"]),
            model_name=row["model_name"],
            date=target_date,
            prediction_score=float(scores[i]),
            predicted_setting=int(settings[i]),
            confidence=float(confidence[i]),
        )
        db.merge(pred)  # upsert

        results.append(
            {
                "machine_number": int(row["machine_number"]),
                "model_name": row["model_name"],
                "prediction_score": float(scores[i]),
                "predicted_setting": int(settings[i]),
                "confidence": float(confidence[i]),
            }
        )

    db.commit()
    return sorted(results, key=lambda x: x["prediction_score"], reverse=True)

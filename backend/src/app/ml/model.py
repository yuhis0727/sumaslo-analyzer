"""MLモデル定義 (Phase1: scikit-learn)

モデル選択の優先順位 (CLAUDE.md):
  1. LightGBM       — メインモデル
  2. ランダムフォレスト — ベースライン・特徴量重要度確認用
  3. ロジスティック回帰 — 最小ベースライン

評価指標:
  Precision, Recall, ROC-AUC
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    import lightgbm as lgb  # Phase1 メインモデル

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from src.app.ml.features import FEATURE_COLUMNS


class SlotSettingModel:
    """高設定台予測モデル

    Phase1: LightGBM (or RandomForest fallback) + LogisticRegression baseline
    """

    def __init__(self, model_type: str = "lightgbm"):
        """
        Args:
            model_type: "lightgbm" | "random_forest" | "logistic"
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = FEATURE_COLUMNS
        self.is_fitted = False

    def _build_model(self):
        if self.model_type == "lightgbm" and HAS_LIGHTGBM:
            return lgb.LGBMClassifier(
                n_estimators=300,
                learning_rate=0.05,
                num_leaves=31,
                max_depth=-1,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                class_weight="balanced",
                verbose=-1,
            )
        elif self.model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        else:
            return LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )

    def _prepare_X(self, df: pd.DataFrame) -> np.ndarray:
        """特徴量行列を準備 (欠損値を中央値で補完)"""
        X = df[self.feature_columns].copy()
        X = X.fillna(X.median())
        return X.values

    def fit(self, df: pd.DataFrame, y: pd.Series) -> dict:
        """モデルを学習する

        Args:
            df: 特徴量 DataFrame (FEATURE_COLUMNS を含む)
            y: ラベル Series (0/1)

        Returns:
            評価指標の辞書

        """
        X = self._prepare_X(df)

        X_train, X_val, y_train, y_val = train_test_split(
            X, y.values, test_size=0.2, random_state=42, stratify=y.values
        )

        # ロジスティック回帰のみ正規化が必要
        if self.model_type == "logistic":
            X_train = self.scaler.fit_transform(X_train)
            X_val = self.scaler.transform(X_val)

        self.model = self._build_model()
        self.model.fit(X_train, y_train)
        self.is_fitted = True

        # 評価
        y_pred = self.model.predict(X_val)
        y_prob = self.model.predict_proba(X_val)[:, 1]

        metrics = {
            "precision": float(precision_score(y_val, y_pred, zero_division=0)),
            "recall": float(recall_score(y_val, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_val, y_prob)),
            "model_type": self.model_type,
            "n_train": len(X_train),
            "n_val": len(X_val),
        }

        # LightGBM / RandomForest の特徴量重要度
        if hasattr(self.model, "feature_importances_"):
            importance = dict(
                zip(self.feature_columns, self.model.feature_importances_.tolist())
            )
            metrics["feature_importance"] = importance

        return metrics

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """高設定確率を予測する

        Returns:
            shape (n,) の確率配列 (高設定=1 の確率)

        """
        if not self.is_fitted:
            raise RuntimeError("モデルが未学習です。fit() を先に呼んでください。")
        X = self._prepare_X(df)
        if self.model_type == "logistic":
            X = self.scaler.transform(X)
        return self.model.predict_proba(X)[:, 1]

    def predict_setting(self, df: pd.DataFrame) -> np.ndarray:
        """予測設定 (1〜6) を推定する (簡易版: スコアを6段階に量子化)"""
        probs = self.predict_proba(df)
        # 0〜1 のスコアを設定1〜6 に対応させる
        settings = np.clip(np.ceil(probs * 6).astype(int), 1, 6)
        return settings

    def save(self, path: str) -> None:
        """モデルをファイルに保存する"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                    "model_type": self.model_type,
                    "feature_columns": self.feature_columns,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "SlotSettingModel":
        """保存済みモデルを読み込む"""
        with open(path, "rb") as f:
            data = pickle.load(f)
        instance = cls(model_type=data["model_type"])
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance.feature_columns = data["feature_columns"]
        instance.is_fitted = True
        return instance

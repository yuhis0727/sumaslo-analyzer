from datetime import datetime

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch import nn


class SlotDataPreprocessor:
    """スロットデータの前処理クラス"""

    def __init__(self):
        self.scaler = StandardScaler()

    def prepare_features(self, machines_data: list[dict]) -> pd.DataFrame:
        """機械学習用の特徴量を準備

        Args:
            machines_data: 台データのリスト

        Returns:
            特徴量のDataFrame

        """
        df = pd.DataFrame(machines_data)

        # 基本統計量の計算
        features = pd.DataFrame()

        # ゲーム数関連
        features["avg_game_count"] = df["game_count"].mean()
        features["std_game_count"] = df["game_count"].std()
        features["max_game_count"] = df["game_count"].max()
        features["min_game_count"] = df["game_count"].min()

        # ボーナス関連
        if "big_bonus" in df.columns:
            features["avg_bb"] = df["big_bonus"].mean()
            features["total_bb"] = df["big_bonus"].sum()
            df["bb_probability"] = df.apply(
                lambda x: x["big_bonus"] / x["game_count"]
                if x["game_count"] > 0
                else 0,
                axis=1,
            )
            features["avg_bb_probability"] = df["bb_probability"].mean()

        # 差枚数関連
        if "total_difference" in df.columns:
            features["avg_difference"] = df["total_difference"].mean()
            features["total_difference"] = df["total_difference"].sum()
            features["positive_machines_ratio"] = (
                (df["total_difference"] > 0).sum() / len(df)
            )

            # 高設定の可能性がある台の割合
            # 差枚数が2000枚以上の台を高設定候補とする
            features["high_setting_candidates"] = (
                (df["total_difference"] > 2000).sum() / len(df)
            )

        # 機種ごとの集計
        if "model_name" in df.columns:
            features["unique_models"] = df["model_name"].nunique()

        return features

    def normalize_features(self, features: pd.DataFrame) -> np.ndarray:
        """特徴量を正規化"""
        return self.scaler.fit_transform(features)


class SettingPredictionModel(nn.Module):
    """設定予測用のニューラルネットワークモデル"""

    def __init__(self, input_size: int, hidden_size: int = 64):
        super().__init__()
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.3)

        self.layer2 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.3)

        self.layer3 = nn.Linear(hidden_size // 2, hidden_size // 4)
        self.relu3 = nn.ReLU()

        # 出力層: 高設定確率を出力
        self.output = nn.Linear(hidden_size // 4, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu1(x)
        x = self.dropout1(x)

        x = self.layer2(x)
        x = self.relu2(x)
        x = self.dropout2(x)

        x = self.layer3(x)
        x = self.relu3(x)

        x = self.output(x)
        x = self.sigmoid(x)
        return x


class SlotAIAnalyzer:
    """スロットデータのAI分析クラス"""

    def __init__(self, model_path: str = None):
        self.preprocessor = SlotDataPreprocessor()
        self.model = None
        self.model_path = model_path

        if model_path:
            self.load_model(model_path)

    def analyze_store(
        self, store_data: dict, historical_data: list[dict] = None,
    ) -> dict:
        """店舗データを分析して高設定台の確率を予測

        Args:
            store_data: 店舗の台データ
            historical_data: 過去のデータ(オプション)

        Returns:
            分析結果

        """
        machines = store_data.get("machines", [])

        if not machines:
            return {
                "high_setting_probability": 0.0,
                "confidence_score": 0.0,
                "recommended_machines": [],
                "analysis_details": {"error": "データが不足しています"},
            }

        # 特徴量の準備
        features = self.preprocessor.prepare_features(machines)

        # 統計的分析
        statistical_analysis = self._statistical_analysis(machines)

        # 推奨台の選定
        recommended_machines = self._select_recommended_machines(machines)

        # モデルがある場合はAI予測を実行
        ai_prediction = None
        if self.model:
            ai_prediction = self._predict_with_model(features)

        # 総合評価
        high_setting_prob = self._calculate_overall_probability(
            statistical_analysis, ai_prediction,
        )

        # 信頼度スコアの計算
        confidence = self._calculate_confidence(len(machines), historical_data)

        return {
            "high_setting_probability": float(high_setting_prob),
            "confidence_score": float(confidence),
            "recommended_machines": recommended_machines,
            "analysis_details": {
                "statistical_analysis": statistical_analysis,
                "ai_prediction": ai_prediction,
                "total_machines": len(machines),
                "analysis_date": datetime.now().isoformat(),
            },
        }

    def _statistical_analysis(self, machines: list[dict]) -> dict:
        """統計的分析を実施"""
        df = pd.DataFrame(machines)

        analysis = {
            "average_game_count": float(df["game_count"].mean())
            if "game_count" in df.columns
            else 0,
            "average_difference": float(df["total_difference"].mean())
            if "total_difference" in df.columns
            else 0,
            "positive_machines_count": int(
                (df["total_difference"] > 0).sum()
                if "total_difference" in df.columns
                else 0,
            ),
            "high_performers": [],
        }

        # 差枚数が高い台をリストアップ
        if "total_difference" in df.columns:
            high_performers = df.nlargest(5, "total_difference")[
                ["machine_number", "model_name", "total_difference"]
            ].to_dict("records")
            analysis["high_performers"] = high_performers

        return analysis

    def _select_recommended_machines(
        self, machines: list[dict], top_n: int = 5,
    ) -> list[int]:
        """推奨台を選定"""
        df = pd.DataFrame(machines)

        if "total_difference" not in df.columns:
            return []

        # 差枚数でソートして上位N台を選択
        top_machines = df.nlargest(top_n, "total_difference")
        return top_machines["machine_number"].tolist()

    def _predict_with_model(self, features: pd.DataFrame) -> float:
        """AIモデルで予測"""
        if not self.model:
            return None

        try:
            # 特徴量を正規化
            normalized = self.preprocessor.normalize_features(features)
            tensor = torch.FloatTensor(normalized)

            # 予測
            self.model.eval()
            with torch.no_grad():
                prediction = self.model(tensor)

            return float(prediction.item())
        except Exception as e:
            print(f"モデル予測エラー: {e}")
            return None

    def _calculate_overall_probability(
        self, statistical: dict, ai_prediction: float = None,
    ) -> float:
        """総合的な高設定確率を計算"""
        # 統計的分析から基本確率を算出
        avg_diff = statistical.get("average_difference", 0)
        positive_ratio = (
            statistical.get("positive_machines_count", 0)
            / statistical.get("total_machines", 1)
            if "total_machines" in statistical
            else 0
        )

        # 簡易的な確率計算
        diff_factor = (avg_diff / 1000) * 0.5
        statistical_prob = min(1.0, max(0.0, diff_factor + positive_ratio * 0.5))

        # AI予測がある場合は加重平均
        if ai_prediction is not None:
            return statistical_prob * 0.4 + ai_prediction * 0.6

        return statistical_prob

    def _calculate_confidence(
        self, machine_count: int, historical_data: list = None,
    ) -> float:
        """信頼度スコアを計算"""
        # データ数に基づく基本信頼度
        base_confidence = min(1.0, machine_count / 50)

        # 履歴データがある場合は信頼度を上げる
        if historical_data and len(historical_data) > 0:
            history_bonus = min(0.3, len(historical_data) * 0.05)
            base_confidence = min(1.0, base_confidence + history_bonus)

        return base_confidence

    def train_model(self, training_data: list[dict], epochs: int = 100):
        """モデルを学習"""
        # 訓練データの準備
        X = []
        y = []

        for data in training_data:
            features = self.preprocessor.prepare_features(data["machines"])
            X.append(features.values[0])
            y.append(data["label"])  # 0 or 1 (低設定 or 高設定)

        X = np.array(X)
        y = np.array(y)

        # データ分割
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42,
        )

        # モデルの初期化
        input_size = X_train.shape[1]
        self.model = SettingPredictionModel(input_size)

        # 訓練
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

        for epoch in range(epochs):
            self.model.train()
            X_tensor = torch.FloatTensor(X_train)
            y_tensor = torch.FloatTensor(y_train).view(-1, 1)

            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()

            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")

    def save_model(self, path: str):
        """モデルを保存"""
        if self.model:
            torch.save(self.model.state_dict(), path)

    def load_model(self, path: str):
        """モデルを読み込み"""
        # モデルのサイズは実際のデータから決定する必要がある
        # ここでは仮の値を使用
        self.model = SettingPredictionModel(input_size=10)
        self.model.load_state_dict(torch.load(path))
        self.model.eval()

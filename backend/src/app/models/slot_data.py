from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.app.models import Base


class Store(Base):
    """店舗情報"""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    area = Column(String(255), nullable=True)
    anaslo_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーション
    machines = relationship("SlotMachine", back_populates="store")
    daily_summaries = relationship("DailyStoreSummary", back_populates="store")
    predictions = relationship("Prediction", back_populates="store")


class SlotMachine(Base):
    """台データ（日付ごとの台別データ）"""

    __tablename__ = "slot_machines"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    machine_number = Column(Integer, nullable=False)  # 台番号
    model_name = Column(String(255), nullable=False)  # 機種名
    game_count = Column(Integer, nullable=True)  # ゲーム数
    big_bonus = Column(Integer, nullable=True)  # BB回数
    regular_bonus = Column(Integer, nullable=True)  # RB回数
    art_count = Column(Integer, nullable=True)  # ART回数
    total_difference = Column(Integer, nullable=True)  # 差枚数
    bb_probability = Column(String(50), nullable=True)  # BB確率（例: "1/250"）
    rb_probability = Column(String(50), nullable=True)  # RB確率（例: "1/350"）
    combined_probability = Column(String(50), nullable=True)  # 合成確率（例: "1/145"）
    data_date = Column(Date, nullable=False)  # データ日付
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ユニーク制約: 同じ店舗・台番号・日付の組み合わせは一意
    __table_args__ = (
        UniqueConstraint(
            "store_id", "machine_number", "data_date", name="uq_machine_date"
        ),
    )

    # リレーション
    store = relationship("Store", back_populates="machines")


class Prediction(Base):
    """AI予測結果"""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    prediction_date = Column(DateTime, nullable=False)  # 予測日
    high_setting_probability = Column(Float, nullable=False)  # 高設定台の確率
    confidence_score = Column(Float, nullable=False)  # 信頼度スコア
    recommended_machines = Column(Text, nullable=True)  # おすすめ台番号(JSON形式)
    analysis_details = Column(Text, nullable=True)  # 分析詳細(JSON形式)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーション
    store = relationship("Store", back_populates="predictions")


class DailyStoreSummary(Base):
    """日付ごとの店舗サマリー"""

    __tablename__ = "daily_store_summaries"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    data_date = Column(Date, nullable=False)  # データ日付
    total_machines = Column(Integer, nullable=False)  # 総台数
    positive_machines = Column(Integer, nullable=True)  # プラス台数
    negative_machines = Column(Integer, nullable=True)  # マイナス台数
    total_difference = Column(Integer, nullable=True)  # 総差枚数
    average_difference = Column(Float, nullable=True)  # 平均差枚数
    average_game_count = Column(Float, nullable=True)  # 平均ゲーム数
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ユニーク制約: 同じ店舗・日付の組み合わせは一意
    __table_args__ = (
        UniqueConstraint("store_id", "data_date", name="uq_store_date_summary"),
    )

    # リレーション
    store = relationship("Store", back_populates="daily_summaries")


class SlotModel(Base):
    """機種マスター"""

    __tablename__ = "slot_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)  # 機種名
    maker = Column(String(255), nullable=True)  # メーカー
    type = Column(String(50), nullable=True)  # タイプ（AT, ART, A+AT等）
    max_payout = Column(Integer, nullable=True)  # 最大払出枚数
    # 設定別機械割（%）
    setting_1_payout = Column(Float, nullable=True)  # 設定1
    setting_2_payout = Column(Float, nullable=True)  # 設定2
    setting_5_payout = Column(Float, nullable=True)  # 設定5
    setting_6_payout = Column(Float, nullable=True)  # 設定6
    # 設定判別ポイント（JSON形式）
    setting_hints = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーション
    daily_summaries = relationship("DailyModelSummary", back_populates="model")


class DailyModelSummary(Base):
    """機種ごとの日付別サマリー（店舗×機種×日付）"""

    __tablename__ = "daily_model_summaries"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("slot_models.id"), nullable=False)
    data_date = Column(Date, nullable=False)
    machine_count = Column(Integer, nullable=False)  # 台数
    total_game_count = Column(Integer, nullable=True)  # 総ゲーム数
    average_game_count = Column(Float, nullable=True)  # 平均ゲーム数
    total_difference = Column(Integer, nullable=True)  # 総差枚数
    average_difference = Column(Float, nullable=True)  # 平均差枚数
    positive_count = Column(Integer, nullable=True)  # プラス台数
    max_difference = Column(Integer, nullable=True)  # 最大差枚数
    min_difference = Column(Integer, nullable=True)  # 最小差枚数
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint(
            "store_id", "model_id", "data_date", name="uq_store_model_date"
        ),
    )

    # リレーション
    model = relationship("SlotModel", back_populates="daily_summaries")


class MachinePositionHistory(Base):
    """台番号履歴（同じ席の過去データ傾向）"""

    __tablename__ = "machine_position_histories"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    machine_number = Column(Integer, nullable=False)  # 台番号
    # 集計期間
    period_start = Column(Date, nullable=False)  # 集計開始日
    period_end = Column(Date, nullable=False)  # 集計終了日
    data_count = Column(Integer, nullable=False)  # データ件数
    # 統計データ
    total_difference = Column(Integer, nullable=True)  # 期間内総差枚
    average_difference = Column(Float, nullable=True)  # 平均差枚
    positive_days = Column(Integer, nullable=True)  # プラスだった日数
    negative_days = Column(Integer, nullable=True)  # マイナスだった日数
    max_difference = Column(Integer, nullable=True)  # 期間内最大差枚
    min_difference = Column(Integer, nullable=True)  # 期間内最小差枚
    # 高設定推測スコア（0-100）
    high_setting_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint(
            "store_id", "machine_number", "period_start", "period_end",
            name="uq_position_period"
        ),
    )


class ScrapingLog(Base):
    """スクレイピング実行ログ"""

    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    status = Column(String(50), nullable=False)  # success, failed, running
    error_message = Column(Text, nullable=True)
    scraped_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

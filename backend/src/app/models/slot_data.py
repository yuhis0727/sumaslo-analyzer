from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
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
    predictions = relationship("Prediction", back_populates="store")


class SlotMachine(Base):
    """台データ"""
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
    data_date = Column(DateTime, nullable=False)  # データ取得日
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

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

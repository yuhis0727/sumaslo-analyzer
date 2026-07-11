from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Date,
)
from sqlalchemy.orm import relationship

from src.app.models import Base


class Store(Base):
    """店舗情報"""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(512), nullable=True)
    prefecture = Column(String(50), nullable=True)
    url = Column(String(512), nullable=True)  # アナスロURL
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    machines = relationship("Machine", back_populates="store")
    scraping_logs = relationship("ScrapingLog", back_populates="store")


class Machine(Base):
    """台データ (machines テーブル)"""

    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    machine_number = Column(Integer, nullable=False)   # 台番号
    model_name = Column(String(255), nullable=False)   # 機種名
    date = Column(Date, nullable=False)                # データ取得日付
    games_played = Column(Integer, nullable=True)      # ゲーム数
    diff_medals = Column(Integer, nullable=True)       # 差枚数
    bonus_count = Column(Integer, nullable=True)       # 総ボーナス回数
    reg_count = Column(Integer, nullable=True)         # REG回数
    big_count = Column(Integer, nullable=True)         # BIG回数
    at_count = Column(Integer, nullable=True)          # ART/AT回数
    created_at = Column(DateTime, default=datetime.now)

    store = relationship("Store", back_populates="machines")


class TheoreticalValue(Base):
    """機種別理論値 (theoretical_values テーブル)"""

    __tablename__ = "theoretical_values"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False)   # 機種名
    setting = Column(Integer, nullable=False)          # 設定 (1〜6)
    reg_prob = Column(Float, nullable=True)            # REG確率 (1/N)
    big_prob = Column(Float, nullable=True)            # BIG確率 (1/N)
    at_rate = Column(Float, nullable=True)             # AT突入率
    diff_rate_per_game = Column(Float, nullable=True)  # 差枚率 (枚/G)
    source_url = Column(String(512), nullable=True)    # 情報ソースURL


class ScrapingLog(Base):
    """スクレイピング実行ログ"""

    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    status = Column(String(50), nullable=False)        # success / failed / running
    error_message = Column(Text, nullable=True)
    scraped_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    store = relationship("Store", back_populates="scraping_logs")

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# .envファイルを読み込む
load_dotenv()

# DATABASE_URLを環境変数から取得、デフォルト値を設定
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://db-user:db-pass@db:3306/f2t?charset=utf8mb4",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# テーブル作成のためにBaseクラスを共有する
Base = declarative_base()

__all__ = []


# テーブル作成
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

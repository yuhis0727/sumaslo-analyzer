"""
DB初期化スクリプト
- マルハン蒲田7のStoreレコードを登録
- CSVデータを machines テーブルに一括インポート

使い方（コンテナ内）:
  python scripts/init_db.py
  python scripts/init_db.py --csv /path/to/machines.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# パス解決
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.app.models import SessionLocal, engine
from src.app.models.slot_data import Machine, Store

STORE_NAME = "マルハン蒲田7"
STORE_URL = "https://ana-slo.com/maruhan-kamata-7/"
DEFAULT_CSV = Path(__file__).parents[1] / "data" / "machines.csv"

CHUNK_SIZE = 2000  # 一度にINSERTする行数


def get_or_create_store(db) -> Store:
    store = db.query(Store).filter(Store.name == STORE_NAME).first()
    if store:
        print(f"[Store] 既存レコード使用: id={store.id}")
        return store
    store = Store(
        name=STORE_NAME,
        address="東京都大田区西蒲田7-68-1",
        prefecture="東京都",
        url=STORE_URL,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    print(f"[Store] 作成: id={store.id}")
    return store


def import_csv(csv_path: Path, store_id: int) -> None:
    print(f"[CSV] 読み込み: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
    df["total_diff"] = pd.to_numeric(df["total_diff"], errors="coerce")
    df["game_count"] = pd.to_numeric(df["game_count"], errors="coerce")
    df = df.dropna(subset=["machine_number", "date"])
    df["machine_number"] = df["machine_number"].astype(int)
    total = len(df)
    print(f"[CSV] {total:,} 行を処理します")

    # 既存データの日付を取得（重複スキップ用）
    with engine.connect() as conn:
        existing_dates = set(
            r[0] for r in conn.execute(
                text("SELECT DISTINCT date FROM machines WHERE store_id = :sid"),
                {"sid": store_id},
            )
        )
    print(f"[DB] 既存日付: {len(existing_dates)} 日分")

    df_new = df[~df["date"].isin(existing_dates)]
    if df_new.empty:
        print("[DB] 新規データなし。スキップ。")
        return
    print(f"[DB] 新規: {len(df_new):,} 行をインポート")

    records = [
        {
            "store_id": store_id,
            "machine_number": int(row["machine_number"]),
            "model_name": str(row["model_name"]),
            "date": row["date"],
            "games_played": int(row["game_count"]) if pd.notna(row.get("game_count")) else None,
            "diff_medals": int(row["total_diff"]) if pd.notna(row.get("total_diff")) else None,
        }
        for _, row in df_new.iterrows()
    ]

    db = SessionLocal()
    try:
        inserted = 0
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i: i + CHUNK_SIZE]
            db.bulk_insert_mappings(Machine, chunk)
            db.commit()
            inserted += len(chunk)
            pct = inserted / len(records) * 100
            print(f"\r  {inserted:,}/{len(records):,} ({pct:.0f}%)", end="", flush=True)
        print(f"\n[DB] インポート完了: {inserted:,} 行")
    except Exception as e:
        db.rollback()
        print(f"\n[DB] エラー: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--store-only", action="store_true", help="Storeレコードのみ登録")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        store = get_or_create_store(db)
    finally:
        db.close()

    if not args.store_only:
        import_csv(Path(args.csv), store.id)

    print("[完了]")


if __name__ == "__main__":
    main()

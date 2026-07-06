"""
毎日の台データをサーバーAPIに送信するスクリプト
bulk_scraper.pyでCSVを更新した後に実行する

使い方:
  python daily_import.py                          # 昨日分をローカルAPIに送信
  python daily_import.py --date 2026-07-05        # 日付指定
  python daily_import.py --server https://your-server.com  # 本番サーバーに送信
  python daily_import.py --token secret-token     # 認証トークン指定
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

DEFAULT_CSV = Path(__file__).parent / "minrepo_maruhan_kamata7_browser.csv"
DEFAULT_SERVER = "http://localhost:8080"
DEFAULT_TOKEN = os.getenv("IMPORT_TOKEN", "")


def load_csv_for_date(csv_path: Path, target_date: date) -> list[dict]:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
    df["total_diff"] = pd.to_numeric(df["total_diff"], errors="coerce")
    df["game_count"] = pd.to_numeric(df["game_count"], errors="coerce")
    df = df[df["date"] == target_date].dropna(subset=["machine_number"])
    df = df.drop_duplicates(subset=["machine_number"])
    df["machine_number"] = df["machine_number"].astype(int)

    return [
        {
            "machine_number": int(row["machine_number"]),
            "model_name": str(row["model_name"]),
            "total_diff": int(row["total_diff"]) if pd.notna(row.get("total_diff")) else None,
            "game_count": int(row["game_count"]) if pd.notna(row.get("game_count")) else None,
        }
        for _, row in df.iterrows()
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="対象日 (YYYY-MM-DD)。未指定で昨日")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    print(f"[送信] 対象日: {target} → {args.server}")

    machines = load_csv_for_date(Path(args.csv), target)
    if not machines:
        print(f"[エラー] {target} のデータがCSVに見つかりません")
        return

    print(f"[CSV] {len(machines)} 台のデータを取得")

    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["X-Import-Token"] = args.token

    resp = requests.post(
        f"{args.server}/api/data/import",
        headers=headers,
        data=json.dumps({"date": target.isoformat(), "machines": machines}, ensure_ascii=False),
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"[完了] upserted={result['upserted']} 台")


if __name__ == "__main__":
    main()

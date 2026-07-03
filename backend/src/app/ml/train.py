"""学習スクリプト

使い方:
    python -m src.app.ml.train --store-id 1 --output models/slot_model.pkl
"""

import argparse
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from src.app.ml.features import (
    build_label_theoretical,
    compute_basic_features,
    compute_context_features,
    compute_deviation_features,
    compute_timeseries_features,
)
from src.app.ml.model import SlotSettingModel
from src.app.models import SessionLocal
from src.app.models.slot_data import Machine, Store, TheoreticalValue


def load_theoretical_values(db: Session) -> dict:
    """theoretical_values テーブルから設定6理論値を取得する"""
    rows = db.query(TheoreticalValue).filter(TheoreticalValue.setting == 6).all()
    return {
        row.model_name: {
            "reg_prob": row.reg_prob,
            "big_prob": row.big_prob,
            "at_rate": row.at_rate,
            "diff_rate_per_game": row.diff_rate_per_game,
        }
        for row in rows
    }


def load_machines(db: Session, store_id: int | None = None) -> pd.DataFrame:
    """machines テーブルからデータを取得する"""
    q = db.query(Machine)
    if store_id:
        q = q.filter(Machine.store_id == store_id)
    rows = q.all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
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
            for r in rows
        ]
    )


def train(
    store_id: int | None = None,
    model_type: str = "lightgbm",
    output_path: str = "models/slot_model.pkl",
) -> dict:
    """学習パイプラインを実行する

    Returns:
        評価指標の辞書

    """
    db: Session = SessionLocal()
    try:
        theoretical = load_theoretical_values(db)
        df = load_machines(db, store_id)
    finally:
        db.close()

    if df.empty:
        raise ValueError("学習データが存在しません。先にスクレイピングを実行してください。")

    all_dates = sorted(df["date"].unique())
    records = []

    for target_date in all_dates:
        day_df = df[df["date"] == target_date].copy()
        history = df[df["date"] < target_date].copy()

        day_df = compute_basic_features(day_df)
        day_df = compute_deviation_features(day_df, theoretical)
        day_df = compute_context_features(day_df, target_date)
        day_df = compute_timeseries_features(day_df, history)
        day_df["label"] = build_label_theoretical(day_df, theoretical)
        records.append(day_df)

    full_df = pd.concat(records, ignore_index=True)
    y = full_df["label"]

    model = SlotSettingModel(model_type=model_type)
    metrics = model.fit(full_df, y)
    model.save(output_path)

    print(f"学習完了: {metrics}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-id", type=int, default=None)
    parser.add_argument("--model-type", default="lightgbm")
    parser.add_argument("--output", default="models/slot_model.pkl")
    args = parser.parse_args()

    train(
        store_id=args.store_id,
        model_type=args.model_type,
        output_path=args.output,
    )

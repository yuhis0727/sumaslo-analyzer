"""
CSV直読みデータAPI - みんレポCSVをpandasで集計して返す
DB不要・即動作
"""
from __future__ import annotations

import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

CSV_PATH = os.environ.get(
    "MACHINES_CSV",
    str(Path(__file__).parents[4] / "data" / "machines.csv"),
)

DOW_JP = ["月", "火", "水", "木", "金", "土", "日"]


@lru_cache(maxsize=1)
def _load_df() -> pd.DataFrame:
    if not Path(CSV_PATH).exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    df["total_diff"] = pd.to_numeric(df["total_diff"], errors="coerce")
    df["game_count"] = pd.to_numeric(df["game_count"], errors="coerce")
    df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
    df = df.dropna(subset=["total_diff", "machine_number"])
    df["machine_number"] = df["machine_number"].astype(int)
    return df


def _get_df() -> pd.DataFrame:
    try:
        return _load_df()
    except Exception:
        _load_df.cache_clear()
        return _load_df()


def _event_days(n: int) -> list[int]:
    """Nの日: n, n+10, n+20"""
    return [n, n + 10, n + 20]


def _today_event_n() -> int:
    day = date.today().day
    if day >= 1 and day <= 9:
        return day
    if day >= 11 and day <= 19:
        return day - 10
    if day >= 21 and day <= 29:
        return day - 20
    return 0  # 10, 20, 30日 = 対象外


# ── /api/data/reload ────────────────────────
@router.post("/data/reload")
def reload_csv():
    """CSVキャッシュをクリアして再読み込み"""
    _load_df.cache_clear()
    df = _get_df()
    return {"rows": len(df), "latest_date": df["date"].max().strftime("%Y-%m-%d")}


# ── /api/data/summary ────────────────────────
@router.get("/data/summary")
def get_summary(n: int | None = Query(None, ge=1, le=9)):
    """
    今日のNの日サマリー。
    n未指定なら今日の日付から自動判定。
    """
    df = _get_df()
    today = date.today()
    event_n = n if n is not None else _today_event_n()

    if event_n == 0:
        return {
            "today": today.isoformat(),
            "day_of_week": DOW_JP[today.weekday()],
            "event_n": None,
            "message": "今日はNの日ではありません",
        }

    days = _event_days(event_n)
    df_n = df[df["date"].dt.day.isin(days)]
    event_dates = sorted(df_n["date"].unique())
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])

    # 台番別勝率（現稼働台限定、最低8日）
    df_n_cur = df_n[df_n["machine_number"].isin(current_machines)]
    machine_stats = (
        df_n_cur.groupby("machine_number")
        .agg(
            model_name=("model_name", lambda x: x.mode()[0]),
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .query("n_days >= 8")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )

    # 機種別勝率
    model_stats = (
        df_n.groupby("model_name")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )

    return {
        "today": today.isoformat(),
        "day_of_week": DOW_JP[today.weekday()],
        "event_n": event_n,
        "event_dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in event_dates],
        "n_event_days": len(event_dates),
        "top_machines": [
            {
                "machine_number": int(r["machine_number"]),
                "model_name": r["model_name"],
                "win_rate": round(r["win_rate"], 4),
                "avg_diff": int(r["avg_diff"]),
                "n_days": int(r["n_days"]),
            }
            for _, r in machine_stats.head(20).iterrows()
        ],
        "top_models": [
            {
                "model_name": r["model_name"],
                "win_rate": round(r["win_rate"], 4),
                "avg_diff": int(r["avg_diff"]),
                "n_days": int(r["n_days"]),
            }
            for _, r in model_stats.head(15).iterrows()
        ],
    }


# ── /api/data/machines ────────────────────────
@router.get("/data/machines")
def get_machines(
    n: int = Query(..., ge=1, le=9),
    min_days: int = Query(5, ge=1),
    limit: int = Query(100, le=500),
):
    """Nの日 台番別勝率一覧"""
    df = _get_df()
    days = _event_days(n)
    df_n = df[df["date"].dt.day.isin(days)]
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    df_n = df_n[df_n["machine_number"].isin(current_machines)]

    stats = (
        df_n.groupby("machine_number")
        .agg(
            model_name=("model_name", lambda x: x.mode()[0]),
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
            total_diff_sum=("total_diff", "sum"),
        )
        .query(f"n_days >= {min_days}")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )

    return [
        {
            "machine_number": int(r["machine_number"]),
            "model_name": r["model_name"],
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
            "total_diff": int(r["total_diff_sum"]),
            "n_days": int(r["n_days"]),
        }
        for _, r in stats.head(limit).iterrows()
    ]


# ── /api/data/machine/{num} ────────────────────────
@router.get("/data/machine/{machine_number}")
def get_machine_history(machine_number: int, n: int | None = Query(None, ge=1, le=9)):
    """特定台番の履歴。n指定でNの日のみ絞り込み"""
    df = _get_df()
    sub = df[df["machine_number"] == machine_number].sort_values("date")
    if sub.empty:
        raise HTTPException(status_code=404, detail="台番が見つかりません")

    if n is not None:
        days = _event_days(n)
        sub = sub[sub["date"].dt.day.isin(days)]

    records = []
    for _, r in sub.iterrows():
        records.append(
            {
                "date": r["date"].strftime("%Y-%m-%d"),
                "model_name": r["model_name"],
                "total_diff": int(r["total_diff"]) if not pd.isna(r["total_diff"]) else None,
                "game_count": int(r["game_count"]) if not pd.isna(r.get("game_count", float("nan"))) else None,
                "day_of_week": DOW_JP[r["date"].weekday()],
                "day": r["date"].day,
            }
        )

    win_rate = (sub["total_diff"] > 0).mean() if len(sub) else 0
    avg_diff = sub["total_diff"].mean() if len(sub) else 0

    return {
        "machine_number": machine_number,
        "model_name": sub["model_name"].mode()[0] if len(sub) else "不明",
        "summary": {
            "n_days": len(sub),
            "win_rate": round(float(win_rate), 4),
            "avg_diff": int(avg_diff) if not pd.isna(avg_diff) else 0,
            "total_diff": int(sub["total_diff"].sum()),
        },
        "records": records,
    }


# ── /api/data/models ────────────────────────
@router.get("/data/models")
def get_models(n: int = Query(..., ge=1, le=9)):
    """Nの日 機種別勝率"""
    df = _get_df()
    days = _event_days(n)
    df_n = df[df["date"].dt.day.isin(days)]

    stats = (
        df_n.groupby("model_name")
        .agg(
            n_machines=("machine_number", "nunique"),
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )

    return [
        {
            "model_name": r["model_name"],
            "n_machines": int(r["n_machines"]),
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
            "n_days": int(r["n_days"]),
        }
        for _, r in stats.iterrows()
    ]


# ── /api/data/recent ────────────────────────
@router.get("/data/recent")
def get_recent(days: int = Query(7, ge=1, le=30)):
    """直近N日の全台データ（最新日から）"""
    df = _get_df()
    latest = df["date"].max()
    cutoff = latest - pd.Timedelta(days=days - 1)
    sub = df[df["date"] >= cutoff]

    by_date = (
        sub.groupby("date")
        .agg(
            total_machines=("machine_number", "count"),
            win_machines=("total_diff", lambda x: (x > 0).sum()),
            avg_diff=("total_diff", "mean"),
        )
        .reset_index()
        .sort_values("date", ascending=False)
    )

    return [
        {
            "date": r["date"].strftime("%Y-%m-%d"),
            "day_of_week": DOW_JP[r["date"].weekday()],
            "total_machines": int(r["total_machines"]),
            "win_machines": int(r["win_machines"]),
            "win_rate": round(r["win_machines"] / r["total_machines"], 4),
            "avg_diff": int(r["avg_diff"]),
        }
        for _, r in by_date.iterrows()
    ]


# ── /api/data/ai-context ────────────────────────
@router.get("/data/ai-context")
def get_ai_context(question: str = Query(...)):
    """AI社員用: 質問に応じた統計コンテキストを返す（Claude API連携用）"""
    df = _get_df()
    today = date.today()
    event_n = _today_event_n()
    latest_date = df["date"].max()

    context = {
        "today": today.isoformat(),
        "day_of_week": DOW_JP[today.weekday()],
        "event_n": event_n,
        "latest_data_date": latest_date.strftime("%Y-%m-%d"),
        "question": question,
    }

    if event_n > 0:
        days = _event_days(event_n)
        df_n = df[df["date"].dt.day.isin(days)]
        current = set(df[df["date"] == latest_date]["machine_number"])
        top = (
            df_n[df_n["machine_number"].isin(current)]
            .groupby("machine_number")
            .agg(
                model=("model_name", lambda x: x.mode()[0]),
                win_rate=("total_diff", lambda x: (x > 0).mean()),
                avg_diff=("total_diff", "mean"),
                n=("total_diff", "count"),
            )
            .query("n >= 8")
            .sort_values(["win_rate", "avg_diff"], ascending=False)
            .head(10)
            .reset_index()
        )
        context["top_picks"] = [
            {"num": int(r["machine_number"]), "model": r["model"],
             "win": f"{r['win_rate']*100:.0f}%", "avg": f"{int(r['avg_diff']):+,}枚"}
            for _, r in top.iterrows()
        ]

    return context

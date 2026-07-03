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


def _current_model_map(df: pd.DataFrame) -> dict[int, str]:
    """最新日の台番→機種名マッピング（配置変更後の現在機種を返す）"""
    latest = df[df["date"] == df["date"].max()]
    return dict(zip(latest["machine_number"], latest["model_name"]))


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
    model_map = _current_model_map(df)

    # 台番別勝率（現稼働台限定、最低8日）
    df_n_cur = df_n[df_n["machine_number"].isin(current_machines)]
    machine_stats = (
        df_n_cur.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .query("n_days >= 8")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )
    machine_stats["model_name"] = machine_stats["machine_number"].map(model_map)

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
    model_map = _current_model_map(df)
    df_n = df_n[df_n["machine_number"].isin(current_machines)]

    stats = (
        df_n.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
            total_diff_sum=("total_diff", "sum"),
        )
        .query(f"n_days >= {min_days}")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )
    stats["model_name"] = stats["machine_number"].map(model_map)

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
    model_map = _current_model_map(df)
    current_model = model_map.get(machine_number, sub["model_name"].mode()[0] if len(sub) else "不明")

    return {
        "machine_number": machine_number,
        "model_name": current_model,
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
        model_map = _current_model_map(df)
        top = (
            df_n[df_n["machine_number"].isin(current)]
            .groupby("machine_number")
            .agg(
                win_rate=("total_diff", lambda x: (x > 0).mean()),
                avg_diff=("total_diff", "mean"),
                n=("total_diff", "count"),
            )
            .query("n >= 8")
            .sort_values(["win_rate", "avg_diff"], ascending=False)
            .head(10)
            .reset_index()
        )
        top["model"] = top["machine_number"].map(model_map)
        context["top_picks"] = [
            {"num": int(r["machine_number"]), "model": r["model"],
             "win": f"{r['win_rate']*100:.0f}%", "avg": f"{int(r['avg_diff']):+,}枚"}
            for _, r in top.iterrows()
        ]

    return context


# ── /api/data/layout-changes ────────────────────────
@router.get("/data/layout-changes")
def get_layout_changes(days: int = Query(30, ge=1, le=180)):
    """
    配置変更アラート。
    直近N日以内に機種名が変わった台番を返す。
    latest_model = 現在の機種、prev_model = 変更前の機種。
    """
    df = _get_df()
    latest_date = df["date"].max()
    cutoff = latest_date - pd.Timedelta(days=days)

    # 台番ごとに時系列で機種名を並べて変化を検出
    changes = []
    for machine_num, grp in df[df["date"] >= cutoff].groupby("machine_number"):
        grp_sorted = grp.sort_values("date")
        models = grp_sorted["model_name"].tolist()
        dates  = grp_sorted["date"].tolist()

        for i in range(1, len(models)):
            if models[i] != models[i - 1]:
                changes.append({
                    "machine_number": int(machine_num),
                    "changed_date": pd.Timestamp(dates[i]).strftime("%Y-%m-%d"),
                    "prev_model": models[i - 1],
                    "latest_model": models[i],
                    "days_since_change": (latest_date - pd.Timestamp(dates[i])).days,
                })

    # 台番ごとに最後の変更のみ残す
    seen: dict[int, dict] = {}
    for c in changes:
        num = c["machine_number"]
        if num not in seen or c["changed_date"] > seen[num]["changed_date"]:
            seen[num] = c

    return sorted(seen.values(), key=lambda x: x["changed_date"], reverse=True)


# ── /api/data/fixed-setting ────────────────────────
@router.get("/data/fixed-setting")
def get_fixed_setting(
    n: int | None = Query(None, ge=1, le=9),
    min_days: int = Query(8, ge=3),
    diff_over_model: int = Query(1000, ge=0),
    consecutive: int = Query(3, ge=1),
):
    """
    固定設定6台の検出。
    「機種の平均差枚を diff_over_model 以上上回り、
     かつ直近 consecutive 回以上連続プラスの台」を返す。
    n指定でNの日限定、未指定で全日。
    """
    df = _get_df()
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    model_map = _current_model_map(df)

    base = df[df["machine_number"].isin(current_machines)]
    if n is not None:
        base = base[base["date"].dt.day.isin(_event_days(n))]

    # 機種平均差枚
    model_avg = (
        base.groupby("model_name")["total_diff"]
        .mean()
        .rename("model_avg_diff")
    )

    # 台番別集計
    machine_stats = (
        base.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .query(f"n_days >= {min_days}")
        .reset_index()
    )
    machine_stats["model_name"] = machine_stats["machine_number"].map(model_map)
    machine_stats = machine_stats.join(model_avg, on="model_name")
    machine_stats["diff_over_model"] = (
        machine_stats["avg_diff"] - machine_stats["model_avg_diff"]
    )

    # 連続プラスチェック（最新 consecutive 回）
    def count_recent_consecutive_plus(machine_num: int) -> int:
        sub = (
            base[base["machine_number"] == machine_num]
            .sort_values("date", ascending=False)["total_diff"]
            .tolist()
        )
        count = 0
        for v in sub:
            if v > 0:
                count += 1
            else:
                break
        return count

    machine_stats["consecutive_plus"] = machine_stats["machine_number"].apply(
        count_recent_consecutive_plus
    )

    result = (
        machine_stats[
            (machine_stats["diff_over_model"] >= diff_over_model)
            & (machine_stats["consecutive_plus"] >= consecutive)
        ]
        .sort_values(["diff_over_model", "win_rate"], ascending=False)
        .reset_index(drop=True)
    )

    return [
        {
            "machine_number": int(r["machine_number"]),
            "model_name": r["model_name"],
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
            "model_avg_diff": int(r["model_avg_diff"]),
            "diff_over_model": int(r["diff_over_model"]),
            "consecutive_plus": int(r["consecutive_plus"]),
            "n_days": int(r["n_days"]),
        }
        for _, r in result.iterrows()
    ]

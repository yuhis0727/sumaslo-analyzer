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

# ── イベントカレンダー ────────────────────────
EVENT_CALENDAR: dict[str, dict] = {
    "ニャンギラス": {
        "dates": [
            "2026-01-01", "2026-01-11", "2026-01-21", "2026-01-31",
            "2026-02-01", "2026-02-11", "2026-02-21",
            "2026-03-01", "2026-03-11", "2026-03-21", "2026-03-31",
            "2026-04-01", "2026-04-11", "2026-04-21",
            "2026-05-01", "2026-05-11", "2026-05-21",
            "2026-06-01", "2026-06-11", "2026-06-21",
            "2026-07-01",
        ],
        "note": "1・11・21・31のつく日。毎月開催のレギュラーイベント。",
    },
    "大田区活性化": {
        "dates": [
            "2026-01-30", "2026-02-28", "2026-03-30", "2026-04-30", "2026-05-30",
            "2026-06-13", "2026-06-30",
        ],
        "note": "月末30日開催。5月で一度終了し6/13に類似イベント再開、6/30から元の形式に戻る。",
    },
    "ファン感謝デー": {
        "dates": [
            "2026-02-13", "2026-02-14", "2026-02-15",
            "2026-05-22", "2026-05-23", "2026-05-24",
        ],
        "note": "年2回の複数日開催。5/22はマルハン創業日。",
    },
}

def _today_events() -> list[str]:
    """今日開催のイベント名一覧"""
    today_str = date.today().isoformat()
    return [name for name, meta in EVENT_CALENDAR.items() if today_str in meta["dates"]]


# ── 機種タイプ判定 ────────────────────────
_BT_MACHINES: frozenset[str] = frozenset({
    "A-SLOT+異世界かるてっとBT",
    "L不二子BT",
    "クレアの秘宝伝～はじまりの扉と太陽の石～ボーナストリガーver.",
    "SHAKE BONUS TRIGGER",
    "マジカルハロウィン ボーナストリガー",
    "バーニングエクスプレス",
})
_A_KEYWORDS: tuple[str, ...] = (
    "ジャグラー", "ハナハナ", "ハナビ", "サンダーV", "沖ドキ", "ディスクアップ", "リオエース", "バーサス",
)


def _model_type(name: str) -> str:
    """機種タイプ判定: AT / A / BT (CSV に列がないため名前から推定)"""
    if name in _BT_MACHINES:
        return "BT"
    if any(k in name for k in _A_KEYWORDS):
        return "A"
    return "AT"


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


# Nの日に該当する日付の日 (N=1-9 → day 1-9, 11-19, 21-29)
_N_DAY_SET: frozenset[int] = frozenset(range(1, 10)) | frozenset(range(11, 20)) | frozenset(range(21, 30))


def _all_event_timestamps() -> set:
    ts: set = set()
    for meta in EVENT_CALENDAR.values():
        ts.update(pd.Timestamp(d) for d in meta["dates"])
    return ts


def _filter_by_event_or_n(
    df: pd.DataFrame,
    n: int | None,
    event: str | None,
    plain: bool = False,
) -> pd.DataFrame:
    """event/n/plain のいずれかでフィルタ。
    plain=True: Nの日でもイベント日でもない平常日のみ残す。"""
    if event is not None:
        if event not in EVENT_CALENDAR:
            raise HTTPException(status_code=400, detail=f"イベント '{event}' は登録されていません")
        event_dates = [pd.Timestamp(d) for d in EVENT_CALENDAR[event]["dates"]]
        return df[df["date"].isin(event_dates)]
    if n is not None:
        return df[df["date"].dt.day.isin(_event_days(n))]
    if plain:
        all_ev = _all_event_timestamps()
        return df[
            ~df["date"].isin(all_ev) &
            ~df["date"].dt.day.isin(_N_DAY_SET)
        ]
    return df


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
    n: int | None = Query(None, ge=1, le=9),
    event: str | None = Query(None),
    plain: bool = Query(False),
    min_days: int = Query(5, ge=1),
    limit: int = Query(100, le=500),
):
    """Nの日/イベント日/平常日の台番別勝率一覧。n・event・plain のいずれかを指定。"""
    if n is None and event is None and not plain:
        raise HTTPException(status_code=400, detail="n・event・plain のいずれかを指定してください")
    df = _get_df()
    df_n = _filter_by_event_or_n(df, n, event, plain)
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
            "machine_type": _model_type(r["model_name"]),
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
            "total_diff": int(r["total_diff_sum"]),
            "n_days": int(r["n_days"]),
        }
        for _, r in stats.head(limit).iterrows()
    ]


# ── /api/data/machine/{num} ────────────────────────
@router.get("/data/machine/{machine_number}")
def get_machine_history(
    machine_number: int,
    n: int | None = Query(None, ge=1, le=9),
    event: str | None = Query(None),
    plain: bool = Query(False),
):
    """特定台番の履歴。n / event / plain で絞り込み可（省略時は全期間）。"""
    df = _get_df()
    sub = df[df["machine_number"] == machine_number].sort_values("date")
    if sub.empty:
        raise HTTPException(status_code=404, detail="台番が見つかりません")
    sub = _filter_by_event_or_n(sub, n, event, plain)

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

    all_records = df[df["machine_number"] == machine_number].sort_values("date")
    win_rate = (sub["total_diff"] > 0).mean() if len(sub) else 0
    avg_diff = sub["total_diff"].mean() if len(sub) else 0
    model_map = _current_model_map(df)
    current_model = model_map.get(machine_number, sub["model_name"].mode()[0] if len(sub) else "不明")

    # 月別集計（全履歴ベース・フィルタなし）
    all_copy = all_records.copy()
    all_copy["ym"] = all_copy["date"].dt.to_period("M")
    monthly = (
        all_copy.groupby("ym")["total_diff"]
        .agg(avg_diff="mean", win_rate=lambda x: (x > 0).mean(), n=("count"))
        .reset_index()
    )
    monthly_list = [
        {
            "month": str(r["ym"]),
            "avg_diff": int(r["avg_diff"]),
            "win_rate": round(r["win_rate"], 4),
            "n": int(r["n"]),
        }
        for _, r in monthly.sort_values("ym").iterrows()
    ]

    # イベント別集計
    event_stats = {}
    for ev_name, meta in EVENT_CALENDAR.items():
        ev_dates = [pd.Timestamp(d) for d in meta["dates"]]
        ev_sub = all_records[all_records["date"].isin(ev_dates)]
        if not ev_sub.empty:
            event_stats[ev_name] = {
                "n_days": len(ev_sub),
                "win_rate": round(float((ev_sub["total_diff"] > 0).mean()), 4),
                "avg_diff": int(ev_sub["total_diff"].mean()),
            }
    # Nの日別集計（N=1〜9）
    n_day_stats = {}
    for nv in range(1, 10):
        nv_sub = all_records[all_records["date"].dt.day.isin(_event_days(nv))]
        if not nv_sub.empty:
            n_day_stats[str(nv)] = {
                "n_days": len(nv_sub),
                "win_rate": round(float((nv_sub["total_diff"] > 0).mean()), 4),
                "avg_diff": int(nv_sub["total_diff"].mean()),
            }

    # 平常日集計（Nの日でもイベント日でもない日）
    plain_sub = _filter_by_event_or_n(all_records, None, None, plain=True)
    plain_stats = (
        {
            "n_days": len(plain_sub),
            "win_rate": round(float((plain_sub["total_diff"] > 0).mean()), 4),
            "avg_diff": int(plain_sub["total_diff"].mean()),
        }
        if not plain_sub.empty
        else None
    )

    return {
        "machine_number": machine_number,
        "machine_type": _model_type(current_model),
        "model_name": current_model,
        "summary": {
            "n_days": len(sub),
            "win_rate": round(float(win_rate), 4),
            "avg_diff": int(avg_diff) if not pd.isna(avg_diff) else 0,
            "total_diff": int(sub["total_diff"].sum()),
        },
        "monthly": monthly_list,
        "event_stats": event_stats,
        "n_day_stats": n_day_stats,
        "plain_stats": plain_stats,
        "records": records,
    }


# ── /api/data/models ────────────────────────
@router.get("/data/models")
def get_models(
    n: int | None = Query(None, ge=1, le=9),
    event: str | None = Query(None),
    plain: bool = Query(False),
):
    """Nの日/イベント日/平常日の機種別勝率。n・event・plain のいずれかを指定。"""
    if n is None and event is None and not plain:
        raise HTTPException(status_code=400, detail="n・event・plain のいずれかを指定してください")
    df = _get_df()
    df_n = _filter_by_event_or_n(df, n, event, plain)

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

    # 直近3ヶ月の月別平均差枚（全日付ベース）
    df["ym"] = df["date"].dt.to_period("M")
    recent_months = sorted(df["ym"].unique())[-3:]
    monthly_avg: dict[str, dict[str, int]] = {}
    for ym in recent_months:
        ym_str = str(ym)
        sub = df[df["ym"] == ym].groupby("model_name")["total_diff"].mean()
        for model, val in sub.items():
            monthly_avg.setdefault(model, {})[ym_str] = int(val)

    return [
        {
            "model_name": r["model_name"],
            "machine_type": _model_type(r["model_name"]),
            "n_machines": int(r["n_machines"]),
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
            "n_days": int(r["n_days"]),
            "monthly_avg": monthly_avg.get(r["model_name"], {}),
        }
        for _, r in stats.iterrows()
    ]


# ── /api/data/model/{name} ────────────────────────
@router.get("/data/model/{model_name}")
def get_model_detail(model_name: str):
    """
    機種詳細。
    - 月別平均差枚（全月）
    - 所属台番一覧と各台の勝率・平均差枚
    """
    df = _get_df()
    latest_date = df["date"].max()
    model_map = _current_model_map(df)

    # 現在この機種に属する台番
    current_machines = [num for num, name in model_map.items() if name == model_name]
    if not current_machines:
        raise HTTPException(status_code=404, detail=f"機種 '{model_name}' が見つかりません")

    base = df[df["machine_number"].isin(current_machines)]

    # 月別平均差枚
    base = base.copy()
    base["ym"] = base["date"].dt.to_period("M")
    monthly = (
        base.groupby("ym")["total_diff"]
        .agg(avg_diff="mean", win_rate=lambda x: (x > 0).mean())
        .reset_index()
    )
    monthly_list = [
        {
            "month": str(r["ym"]),
            "avg_diff": int(r["avg_diff"]),
            "win_rate": round(r["win_rate"], 4),
        }
        for _, r in monthly.sort_values("ym").iterrows()
    ]

    # 台番別集計
    machine_stats = (
        base.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
            total_diff=("total_diff", "sum"),
        )
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .reset_index()
    )

    return {
        "model_name": model_name,
        "machine_type": _model_type(model_name),
        "machine_count": len(current_machines),
        "overall": {
            "win_rate": round(float((base["total_diff"] > 0).mean()), 4),
            "avg_diff": int(base["total_diff"].mean()),
            "total_diff": int(base["total_diff"].sum()),
        },
        "monthly": monthly_list,
        "machines": [
            {
                "machine_number": int(r["machine_number"]),
                "n_days": int(r["n_days"]),
                "win_rate": round(r["win_rate"], 4),
                "avg_diff": int(r["avg_diff"]),
                "total_diff": int(r["total_diff"]),
            }
            for _, r in machine_stats.iterrows()
        ],
    }


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

    today_events = _today_events()
    context = {
        "today": today.isoformat(),
        "day_of_week": DOW_JP[today.weekday()],
        "event_n": event_n,
        "latest_data_date": latest_date.strftime("%Y-%m-%d"),
        "question": question,
        "today_special_events": today_events,
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


# ── /api/data/events ────────────────────────
@router.get("/data/events")
def get_events():
    """イベントカレンダー一覧とCSV内に存在する日付を返す"""
    df = _get_df()
    csv_dates = set(df["date"].dt.strftime("%Y-%m-%d").unique())
    result = []
    for name, meta in EVENT_CALENDAR.items():
        dates_in_csv = [d for d in meta["dates"] if d in csv_dates]
        result.append({
            "event_name": name,
            "note": meta["note"],
            "total_dates": len(meta["dates"]),
            "dates_in_data": len(dates_in_csv),
            "dates": meta["dates"],
        })
    return result


# ── /api/data/event-analysis ────────────────────────
@router.get("/data/event-analysis")
def get_event_analysis(event: str = Query(...)):
    """
    イベント別データ分析。
    各イベント日の店舗全体実績・機種別・台番別ランキングを返す。
    """
    if event not in EVENT_CALENDAR:
        raise HTTPException(status_code=404, detail=f"イベント '{event}' は登録されていません")

    df = _get_df()
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    model_map = _current_model_map(df)

    event_dates_all = [pd.Timestamp(d) for d in EVENT_CALENDAR[event]["dates"]]
    event_df = df[df["date"].isin(event_dates_all)]

    if event_df.empty:
        return {"event_name": event, "dates_summary": [], "top_models": [], "top_machines": []}

    # 日別サマリー
    by_date = (
        event_df.groupby("date")
        .agg(
            total_machines=("machine_number", "count"),
            plus_machines=("total_diff", lambda x: (x > 0).sum()),
            avg_diff=("total_diff", "mean"),
        )
        .reset_index()
        .sort_values("date")
    )
    dates_summary = [
        {
            "date": r["date"].strftime("%Y-%m-%d"),
            "day_of_week": DOW_JP[r["date"].weekday()],
            "total_machines": int(r["total_machines"]),
            "plus_machines": int(r["plus_machines"]),
            "positive_rate": round(r["plus_machines"] / r["total_machines"], 4),
            "avg_diff": int(r["avg_diff"]),
        }
        for _, r in by_date.iterrows()
    ]

    # 現在稼働台限定で機種別集計
    cur_event_df = event_df[event_df["machine_number"].isin(current_machines)].copy()
    cur_event_df["current_model"] = cur_event_df["machine_number"].map(model_map)

    top_models = (
        cur_event_df.groupby("current_model")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .query("n_days >= 2")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .head(20)
        .reset_index()
    )
    top_models_list = [
        {
            "model_name": r["current_model"],
            "n_days": int(r["n_days"]),
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
        }
        for _, r in top_models.iterrows()
    ]

    # 台番別集計
    top_machines = (
        cur_event_df.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
        )
        .query("n_days >= 2")
        .sort_values(["win_rate", "avg_diff"], ascending=False)
        .head(30)
        .reset_index()
    )
    top_machines["model_name"] = top_machines["machine_number"].map(model_map)
    top_machines_list = [
        {
            "machine_number": int(r["machine_number"]),
            "model_name": r["model_name"],
            "n_days": int(r["n_days"]),
            "win_rate": round(r["win_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
        }
        for _, r in top_machines.iterrows()
    ]

    # 全体平均（比較用）
    overall_avg = int(df[df["machine_number"].isin(current_machines)]["total_diff"].mean())

    return {
        "event_name": event,
        "note": EVENT_CALENDAR[event]["note"],
        "dates_summary": dates_summary,
        "top_models": top_models_list,
        "top_machines": top_machines_list,
        "overall_avg_diff": overall_avg,
    }


# ── /api/data/zentai-history ────────────────────────
@router.get("/data/zentai-history")
def get_zentai_history(
    n: int | None = Query(None, ge=1, le=9),
    event: str | None = Query(None),
    positive_rate_threshold: float = Query(0.65, ge=0.0, le=1.0),
    min_machines: int = Query(3, ge=1),
):
    """
    全台系パターン検知。n か event で絞り込み可。未指定で全日付。
    """
    df = _get_df()
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    model_map = _current_model_map(df)

    base = df[df["machine_number"].isin(current_machines)].copy()
    base["current_model"] = base["machine_number"].map(model_map)
    base = _filter_by_event_or_n(base, n, event)

    # 日 × 機種ごとに集計
    day_model = (
        base.groupby(["date", "current_model"])
        .agg(
            total_machines=("machine_number", "nunique"),
            plus_machines=("total_diff", lambda x: (x > 0).sum()),
            avg_diff=("total_diff", "mean"),
            total_diff_sum=("total_diff", "sum"),
        )
        .reset_index()
    )
    day_model["positive_rate"] = day_model["plus_machines"] / day_model["total_machines"]
    day_model["is_zentai"] = (
        (day_model["positive_rate"] >= positive_rate_threshold)
        & (day_model["total_machines"] >= min_machines)
    )
    day_model["event_day"] = day_model["date"].dt.day.apply(
        lambda d: d if d <= 9 else d - 10 if d <= 19 else d - 20
    )

    zentai = day_model[day_model["is_zentai"]].copy()
    zentai["date_str"] = zentai["date"].dt.strftime("%Y-%m-%d")

    return [
        {
            "date": r["date_str"],
            "event_n": int(r["event_day"]),
            "model_name": r["current_model"],
            "total_machines": int(r["total_machines"]),
            "plus_machines": int(r["plus_machines"]),
            "positive_rate": round(r["positive_rate"], 4),
            "avg_diff": int(r["avg_diff"]),
        }
        for _, r in zentai.sort_values("date", ascending=False).iterrows()
    ]


# ── /api/data/model-score ────────────────────────
@router.get("/data/model-score")
def get_model_score(
    n: int | None = Query(None, ge=1, le=9),
    event: str | None = Query(None),
    positive_rate_threshold: float = Query(0.65, ge=0.0, le=1.0),
    min_machines: int = Query(3, ge=1),
    min_event_days: int = Query(5, ge=1),
):
    """
    機種ごとの全台系期待度スコア。n か event で絞り込み可。
    """
    df = _get_df()
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    model_map = _current_model_map(df)

    base = df[df["machine_number"].isin(current_machines)].copy()
    base["current_model"] = base["machine_number"].map(model_map)
    base = _filter_by_event_or_n(base, n, event)

    # 日 × 機種集計
    day_model = (
        base.groupby(["date", "current_model"])
        .agg(
            total_machines=("machine_number", "nunique"),
            plus_machines=("total_diff", lambda x: (x > 0).sum()),
            avg_diff=("total_diff", "mean"),
        )
        .reset_index()
    )
    day_model["positive_rate"] = day_model["plus_machines"] / day_model["total_machines"]
    day_model["is_zentai"] = (
        (day_model["positive_rate"] >= positive_rate_threshold)
        & (day_model["total_machines"] >= min_machines)
    )

    # 機種ごとにスコア集計
    scores = []
    for model_name, grp in day_model.groupby("current_model"):
        total_days = len(grp)
        if total_days < min_event_days:
            continue
        zentai_days = grp[grp["is_zentai"]]
        zentai_count = len(zentai_days)
        zentai_rate = zentai_count / total_days
        avg_zentai_diff = int(zentai_days["avg_diff"].mean()) if zentai_count > 0 else 0
        avg_all_diff = int(grp["avg_diff"].mean())
        machine_count = int(grp["total_machines"].iloc[0])

        # 直近3回が全台系かどうか
        recent = grp.sort_values("date", ascending=False).head(3)
        recent_zentai = int(recent["is_zentai"].sum())

        scores.append({
            "model_name": model_name,
            "machine_count": machine_count,
            "total_event_days": total_days,
            "zentai_count": zentai_count,
            "zentai_rate": round(zentai_rate, 4),
            "avg_zentai_diff": avg_zentai_diff,
            "avg_all_diff": avg_all_diff,
            "recent_zentai_3": recent_zentai,
            # スコア = 全台系頻度 × 全台系時の平均差枚（マイナスは0扱い）
            "score": round(zentai_rate * max(avg_zentai_diff, 0), 1),
        })

    return sorted(scores, key=lambda x: x["score"], reverse=True)


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
    event: str | None = Query(None),
    min_days: int = Query(8, ge=3),
    diff_over_model: int = Query(1000, ge=0),
    consecutive: int = Query(3, ge=1),
):
    """
    固定設定6台の検出。n か event で絞り込み可。
    日ごとの偏差ベースで全台系ノイズを除去する。
    """
    df = _get_df()
    latest_date = df["date"].max()
    current_machines = set(df[df["date"] == latest_date]["machine_number"])
    model_map = _current_model_map(df)

    base = df[df["machine_number"].isin(current_machines)].copy()
    base["current_model"] = base["machine_number"].map(model_map)
    base = _filter_by_event_or_n(base, n, event)

    # 同じ日・同じ機種（現在機種）の平均差枚
    model_daily_avg = (
        base.groupby(["date", "current_model"])["total_diff"]
        .mean()
        .rename("model_daily_avg")
        .reset_index()
    )
    base = base.merge(model_daily_avg, on=["date", "current_model"], how="left")

    # 日ごとの偏差: その台が当日の機種平均をどれだけ上回ったか
    base["day_deviation"] = base["total_diff"] - base["model_daily_avg"]
    # 機種平均を上回ったか（全台系日ではほぼ全台≈0なのでフラット）
    base["beat_model"] = base["day_deviation"] > 0

    # 台番別集計
    machine_stats = (
        base.groupby("machine_number")
        .agg(
            n_days=("total_diff", "count"),
            avg_diff=("total_diff", "mean"),
            avg_day_deviation=("day_deviation", "mean"),
            win_rate_vs_model=("beat_model", "mean"),  # 機種平均超えた日の割合
        )
        .query(f"n_days >= {min_days}")
        .reset_index()
    )
    machine_stats["model_name"] = machine_stats["machine_number"].map(model_map)

    # 機種全体の平均差枚（参考表示用）
    model_overall_avg = (
        base.groupby("current_model")["total_diff"].mean().rename("model_avg_diff")
    )
    machine_stats = machine_stats.join(model_overall_avg, on="model_name")

    # 連続偏差プラスチェック（直近N回、機種平均超えベース）
    def count_consecutive_beat(machine_num: int) -> int:
        sub = (
            base[base["machine_number"] == machine_num]
            .sort_values("date", ascending=False)["beat_model"]
            .tolist()
        )
        count = 0
        for v in sub:
            if v:
                count += 1
            else:
                break
        return count

    machine_stats["consecutive_beat"] = machine_stats["machine_number"].apply(
        count_consecutive_beat
    )

    result = (
        machine_stats[
            (machine_stats["avg_day_deviation"] >= diff_over_model)
            & (machine_stats["consecutive_beat"] >= consecutive)
        ]
        .sort_values(["avg_day_deviation", "win_rate_vs_model"], ascending=False)
        .reset_index(drop=True)
    )

    return [
        {
            "machine_number": int(r["machine_number"]),
            "model_name": r["model_name"],
            "win_rate_vs_model": round(r["win_rate_vs_model"], 4),
            "avg_diff": int(r["avg_diff"]),
            "model_avg_diff": int(r["model_avg_diff"]),
            "avg_day_deviation": int(r["avg_day_deviation"]),
            "consecutive_beat": int(r["consecutive_beat"]),
            "n_days": int(r["n_days"]),
        }
        for _, r in result.iterrows()
    ]


# ── /api/data/new-machines ────────────────────────
@router.get("/data/new-machines")
def get_new_machines(intro_threshold_days: int = Query(30, ge=7)):
    """
    新台分析。データ開始日から intro_threshold_days 日以降に
    初登場した機種を「新台」とみなし、導入週別の実績を返す。
    """
    df = _get_df()
    first_date = df["date"].min()
    latest_date = df["date"].max()

    # 機種の初登場日
    model_intro = (
        df.groupby("model_name")["date"]
        .min()
        .reset_index()
        .rename(columns={"date": "intro_date"})
    )
    cutoff = first_date + pd.Timedelta(days=intro_threshold_days)
    new_models = model_intro[model_intro["intro_date"] >= cutoff].copy()

    if new_models.empty:
        return {"models": [], "weekly_aggregate": []}

    # 日付ごとの店舗全体平均（比較用）
    store_daily_avg = (
        df.groupby("date")["total_diff"]
        .mean()
        .reset_index()
        .rename(columns={"total_diff": "store_avg"})
    )

    models_out = []
    # 週別集計用バッファ (week_num -> list of diffs)
    week_bucket: dict[int, list[float]] = {}

    for _, row in new_models.sort_values("intro_date", ascending=False).iterrows():
        model_name = row["model_name"]
        intro_date = row["intro_date"]
        mdf = df[df["model_name"] == model_name].copy()
        mdf["days_since"] = (mdf["date"] - intro_date).dt.days
        mdf["week"] = (mdf["days_since"] // 7 + 1).clip(upper=8)  # 8週目以降を8+に丸める

        # 店舗平均との比較（同日）
        mdf = mdf.merge(store_daily_avg, on="date", how="left")
        mdf["vs_store"] = mdf["total_diff"] - mdf["store_avg"]

        # 週別集計
        weekly_rows = []
        for wk in sorted(mdf["week"].unique()):
            sub = mdf[mdf["week"] == wk]
            wr = float((sub["total_diff"] > 0).mean())
            avg = float(sub["total_diff"].mean())
            vs = float(sub["vs_store"].mean())
            n = len(sub)
            weekly_rows.append({
                "week": int(wk),
                "win_rate": round(wr, 4),
                "avg_diff": int(avg),
                "vs_store": int(vs),
                "n": n,
            })
            bucket = week_bucket.setdefault(int(wk), [])
            bucket.extend(sub["total_diff"].tolist())

        total_days = int((latest_date - intro_date).days)
        overall_wr = float((mdf["total_diff"] > 0).mean())
        overall_avg = int(mdf["total_diff"].mean())

        models_out.append({
            "model_name": model_name,
            "machine_type": _model_type(model_name),
            "intro_date": intro_date.strftime("%Y-%m-%d"),
            "total_days": total_days,
            "n_data_days": len(mdf),
            "overall_win_rate": round(overall_wr, 4),
            "overall_avg_diff": overall_avg,
            "weekly": weekly_rows,
        })

    # 全新台集計（週別）
    weekly_agg = []
    for wk in sorted(week_bucket.keys()):
        diffs = week_bucket[wk]
        weekly_agg.append({
            "week": wk,
            "avg_diff": int(sum(diffs) / len(diffs)),
            "win_rate": round(sum(1 for d in diffs if d > 0) / len(diffs), 4),
            "n": len(diffs),
        })

    return {"models": models_out, "weekly_aggregate": weekly_agg}

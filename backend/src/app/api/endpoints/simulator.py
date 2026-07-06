"""
入場番号シミュレーター
番号を入れると良番/中番/悪番を判定し、狙い台ランキングを返す
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Query

from .csv_data import (
    _event_days, _get_df, _model_type, _today_event_n, _today_events,
    _current_model_map, _all_event_timestamps, _N_DAY_SET, EVENT_CALENDAR,
    _filter_current_model_only,
)

router = APIRouter()


def _tier(number: int, total: int) -> tuple[str, float]:
    """番号から良番/中番/悪番と上位%を返す"""
    pct = (total - number + 1) / total * 100
    if pct >= 75:
        return "良番", pct
    if pct >= 25:
        return "中番", pct
    return "悪番", pct


def _fixed6_machines(df: pd.DataFrame, current: set[int]) -> set[int]:
    """機種日次平均との偏差が安定してプラスの台（固定設定6候補）"""
    from .csv_data import _filter_current_model_only
    # 現在の機種名のデータのみを使う（旧機種データを除外）
    df_cur = _filter_current_model_only(df[df["machine_number"].isin(current)])
    model_daily = (
        df_cur.groupby(["date", "model_name"])["total_diff"]
        .mean().reset_index().rename(columns={"total_diff": "model_avg"})
    )
    dev = df_cur.merge(model_daily, on=["date", "model_name"])
    dev["deviation"] = dev["total_diff"] - dev["model_avg"]
    stats = (
        dev.groupby("machine_number")
        .agg(avg_dev=("deviation", "mean"), n=("deviation", "count"))
        .query("n >= 30 and avg_dev >= 500")
    )
    return set(stats.index)


@router.get("/simulator/recommend")
def recommend(
    number: int = Query(..., ge=1, description="抽選番号"),
    total: int = Query(200, ge=1, description="推定参加者数"),
):
    df = _get_df()
    today = date.today()
    event_n = _today_event_n()
    today_events = _today_events()
    latest_date = df["date"].max()
    model_map = _current_model_map(df)
    current = set(df[df["date"] == latest_date]["machine_number"])

    tier, pct = _tier(number, total)

    # ── 今日の日種でフィルタ ──
    if event_n > 0:
        base = df[df["date"].dt.day.isin(_event_days(event_n))]
        day_label = f"{event_n}の日"
    elif today_events:
        ev_dates: list = []
        for ev in today_events:
            ev_dates.extend(pd.Timestamp(d) for d in EVENT_CALENDAR[ev]["dates"])
        base = df[df["date"].isin(ev_dates)]
        day_label = "・".join(today_events)
    else:
        all_ev = _all_event_timestamps()
        base = df[~df["date"].isin(all_ev) & ~df["date"].dt.day.isin(_N_DAY_SET)]
        day_label = "平常日"

    base = base[base["machine_number"].isin(current)].copy()
    # 現在の機種名のデータのみに絞る（配置変更前の旧機種データを除外）
    base = _filter_current_model_only(base)

    # 台番別集計（最低5日）
    mstats = (
        base.groupby("machine_number")
        .agg(
            win_rate=("total_diff", lambda x: (x > 0).mean()),
            avg_diff=("total_diff", "mean"),
            n=("total_diff", "count"),
        )
        .query("n >= 5")
        .reset_index()
    )
    mstats["model_name"] = mstats["machine_number"].map(model_map)
    mstats["machine_type"] = mstats["model_name"].map(_model_type)

    fixed6 = _fixed6_machines(df, current)

    latest_counts = df[df["date"] == latest_date].groupby("model_name")["machine_number"].count()
    small_models = set(latest_counts[latest_counts <= 4].index)

    # ── 推薦リスト構築 ──
    seen: set[int] = set()
    recs: list[dict] = []

    def push(num: int, reason: str) -> None:
        if num in seen or num not in mstats["machine_number"].values:
            return
        seen.add(num)
        r = mstats[mstats["machine_number"] == num].iloc[0]
        tags = []
        if num in fixed6:
            tags.append("固定6候補")
        if r["model_name"] in small_models:
            tags.append("少数台")
        recs.append({
            "priority": len(recs) + 1,
            "machine_number": int(num),
            "model_name": r["model_name"],
            "machine_type": r["machine_type"],
            "win_rate": round(float(r["win_rate"]), 4),
            "avg_diff": int(r["avg_diff"]),
            "n_days": int(r["n"]),
            "reason": reason,
            "tags": tags,
            "is_fixed6": num in fixed6,
            "is_small_model": r["model_name"] in small_models,
        })

    top_all = mstats.sort_values(["win_rate", "avg_diff"], ascending=False)
    top_a = mstats[mstats["machine_type"] == "A"].sort_values(["win_rate", "avg_diff"], ascending=False)
    top_f6 = mstats[mstats["machine_number"].isin(fixed6)].sort_values("avg_diff", ascending=False)
    top_small = mstats[mstats["model_name"].isin(small_models)].sort_values(["win_rate", "avg_diff"], ascending=False)

    if tier == "良番":
        # 全種TOP → 固定6補完
        for _, r in top_all.head(8).iterrows():
            push(r["machine_number"], "今日の最良ポジション")
        for _, r in top_f6.head(4).iterrows():
            push(r["machine_number"], "固定設定6候補")

    elif tier == "中番":
        # 固定6 → 少数台全台系 → 高勝率で補完
        for _, r in top_f6.head(5).iterrows():
            push(r["machine_number"], "固定設定6候補")
        for _, r in top_small.head(5).iterrows():
            push(r["machine_number"], "少数台全台系候補")
        for _, r in top_all.head(10).iterrows():
            if len(recs) >= 10:
                break
            push(r["machine_number"], "高勝率台")

    else:  # 悪番
        # Aタイプ台番実績 → 固定6 → 少数台
        for _, r in top_a.head(5).iterrows():
            push(r["machine_number"], "Aタイプ台番実績")
        for _, r in top_f6.head(4).iterrows():
            push(r["machine_number"], "固定設定6候補")
        for _, r in top_small.head(3).iterrows():
            push(r["machine_number"], "少数台全台系候補")

    strategy_map = {
        "良番": "最良ポジションを確保できる番号。本命機種の最高実績台を最優先で取りに行く。本命が埋まっていた場合の第2・第3候補も把握しておく。",
        "中番": "本命は取れない前提で動く。固定設定6台と少数台全台系機種が主戦場。良番が流れた後の空きポジションを狙う。",
        "悪番": "台番実績が信頼できるAタイプを最優先。固定設定6台は良番でも取られない場合がある。勝率重視で座る台を選ぶ。",
    }

    return {
        "number": number,
        "total": total,
        "percentile": round(pct, 1),
        "tier": tier,
        "today": today.isoformat(),
        "day_label": day_label,
        "event_n": event_n,
        "today_events": today_events,
        "strategy": strategy_map[tier],
        "data_basis": f"{day_label}のデータ（最低5回以上の台を対象）",
        "recommendations": recs,
    }

"""
予測ログ・的中検証
シミュレーターの推奨結果を保存し、後日 machines.csv の実データと自動照合して
的中/外れを記録する（検証ループ）。
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from .csv_data import _get_df

router = APIRouter()

PREDICTIONS_PATH = os.environ.get(
    "PREDICTIONS_JSON",
    str(Path(__file__).parents[4] / "data" / "predictions.json"),
)


def _load() -> dict:
    p = Path(PREDICTIONS_PATH)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    Path(PREDICTIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(PREDICTIONS_PATH).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class RecommendationIn(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    priority: int
    machine_number: int
    model_name: str
    machine_type: str
    win_rate: float
    avg_diff: int
    n_days: int
    reason: str
    tags: list[str] = []
    is_fixed6: bool = False
    is_small_model: bool = False


class PredictionPayload(BaseModel):
    number: int
    total: int
    tier: str
    day_label: str
    event_n: int
    recommendations: list[RecommendationIn]


def _reconcile(entry: dict, df) -> dict:
    """保存済みエントリの各推奨台を実データと照合し、hit/actual_diffを付与する。"""
    entry_date = entry["date"]
    day_df = df[df["date"].dt.strftime("%Y-%m-%d") == entry_date]
    actuals = dict(zip(day_df["machine_number"], day_df["total_diff"]))

    recs = []
    hits = 0
    judged = 0
    for r in entry["recommendations"]:
        actual = actuals.get(r["machine_number"])
        hit = None
        if actual is not None:
            hit = bool(actual > 0)
            judged += 1
            if hit:
                hits += 1
        recs.append({
            **r,
            "actual_diff": None if actual is None else int(actual),
            "hit": hit,
        })

    return {
        **entry,
        "recommendations": recs,
        "hit_rate": round(hits / judged, 4) if judged > 0 else None,
        "judged_count": judged,
        "total_count": len(recs),
    }


@router.post("/predictions")
def save_prediction(payload: PredictionPayload):
    """今日のシミュレーター推奨結果を保存する。"""
    today = date.today().isoformat()
    data = _load()
    entries = data.setdefault(today, [])

    entry = {
        "id": uuid4().hex[:8],
        "date": today,
        "saved_at": datetime.now().isoformat(timespec="minutes"),
        "number": payload.number,
        "total": payload.total,
        "tier": payload.tier,
        "day_label": payload.day_label,
        "event_n": payload.event_n,
        "recommendations": [r.model_dump() for r in payload.recommendations],
        "note": "",
    }
    entries.append(entry)
    _save(data)

    return _reconcile(entry, _get_df())


@router.get("/predictions")
def get_predictions(target_date: str | None = Query(None, alias="date")):
    """指定日（省略時は今日）の保存済み予測を、実データと照合して返す。"""
    d = target_date or date.today().isoformat()
    data = _load()
    entries = data.get(d, [])
    df = _get_df()
    return [_reconcile(e, df) for e in entries]


@router.get("/predictions/history")
def get_prediction_history(limit: int = Query(30, ge=1, le=180)):
    """直近N日分の保存済み予測を新しい順で返す（照合済み）。"""
    data = _load()
    df = _get_df()
    dates = sorted(data.keys(), reverse=True)[:limit]

    result = []
    for d in dates:
        for entry in data[d]:
            result.append(_reconcile(entry, df))
    result.sort(key=lambda e: (e["date"], e["saved_at"]), reverse=True)
    return result


class NotePayload(BaseModel):
    note: str


@router.patch("/predictions/{target_date}/{entry_id}")
def update_prediction_note(target_date: str, entry_id: str, payload: NotePayload):
    """的中/外れの原因分析メモを保存する。"""
    data = _load()
    entries = data.get(target_date, [])
    for entry in entries:
        if entry["id"] == entry_id:
            entry["note"] = payload.note
            _save(data)
            return _reconcile(entry, _get_df())
    raise HTTPException(status_code=404, detail="予測エントリが見つかりません")

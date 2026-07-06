"""
今日の示唆情報入力・取得エンドポイント
ウスイ店長X・ococoichi・LINEオープンチャットの内容を保存する
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

HINTS_PATH = os.environ.get(
    "HINTS_JSON",
    str(Path(__file__).parents[4] / "data" / "hints.json"),
)


def _load() -> dict:
    p = Path(HINTS_PATH)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    Path(HINTS_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(HINTS_PATH).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class HintPayload(BaseModel):
    store_post: str = ""
    cocochi: str = ""
    openchat: str = ""


class HintResponse(BaseModel):
    date: str
    store_post: str
    cocochi: str
    openchat: str
    saved_at: str | None


@router.get("/hints/today", response_model=HintResponse)
def get_today_hints():
    """今日の示唆情報を取得"""
    today = date.today().isoformat()
    data = _load()
    entry = data.get(today, {})
    return HintResponse(
        date=today,
        store_post=entry.get("store_post", ""),
        cocochi=entry.get("cocochi", ""),
        openchat=entry.get("openchat", ""),
        saved_at=entry.get("saved_at"),
    )


@router.post("/hints/today", response_model=HintResponse)
def save_today_hints(payload: HintPayload):
    """今日の示唆情報を保存（上書き）"""
    today = date.today().isoformat()
    data = _load()
    data[today] = {
        "store_post": payload.store_post,
        "cocochi": payload.cocochi,
        "openchat": payload.openchat,
        "saved_at": datetime.now().isoformat(timespec="minutes"),
    }
    _save(data)
    return HintResponse(
        date=today,
        store_post=payload.store_post,
        cocochi=payload.cocochi,
        openchat=payload.openchat,
        saved_at=data[today]["saved_at"],
    )


def get_today_hints_context() -> str:
    """ai_chat.py から呼ばれる。今日の示唆テキストをコンテキスト文字列で返す。"""
    today = date.today().isoformat()
    data = _load()
    entry = data.get(today, {})

    lines: list[str] = []
    if entry.get("store_post"):
        lines.append(f"【ウスイ店長のXポスト（{today}）】\n{entry['store_post']}")
    if entry.get("cocochi"):
        lines.append(f"【ococoichiのXポスト（{today}）】\n{entry['cocochi']}")
    if entry.get("openchat"):
        lines.append(f"【LINEオープンチャット情報（{today}）】\n{entry['openchat']}")

    if not lines:
        return ""
    return "\n\n".join(lines)

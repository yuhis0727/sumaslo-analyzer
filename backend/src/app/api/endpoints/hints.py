"""
今日の示唆情報入力・取得エンドポイント
ウスイ店長X・ococoichi・LINEオープンチャットの内容を保存する
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from ... import stores

router = APIRouter()


def _load() -> dict:
    p = Path(stores.hints_path())
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    p = Path(stores.hints_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class HintPayload(BaseModel):
    store_post: str = ""
    cocochi: str = ""
    openchat: str = ""
    # base64文字列のリスト（data URL形式: "data:image/jpeg;base64,..."）
    store_images: list[str] = []
    cocochi_images: list[str] = []


class HintResponse(BaseModel):
    date: str
    store_post: str
    cocochi: str
    openchat: str
    saved_at: str | None
    has_store_images: bool = False
    has_cocochi_images: bool = False


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
        has_store_images=bool(entry.get("store_images")),
        has_cocochi_images=bool(entry.get("cocochi_images")),
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
        "store_images": payload.store_images,
        "cocochi_images": payload.cocochi_images,
        "saved_at": datetime.now().isoformat(timespec="minutes"),
    }
    _save(data)
    return HintResponse(
        date=today,
        store_post=payload.store_post,
        cocochi=payload.cocochi,
        openchat=payload.openchat,
        saved_at=data[today]["saved_at"],
        has_store_images=bool(payload.store_images),
        has_cocochi_images=bool(payload.cocochi_images),
    )


def get_today_hints_context() -> tuple[str, list[dict]]:
    """ai_chat.py から呼ばれる。
    (テキスト文字列, Claudeイメージブロックリスト) を返す。"""
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

    text = "\n\n".join(lines)

    # 画像ブロック構築（Claude Vision API 形式）
    image_blocks: list[dict] = []
    for label, key in [("ウスイ店長", "store_images"), ("ococoichi", "cocochi_images")]:
        for i, data_url in enumerate(entry.get(key, []), 1):
            # data:image/jpeg;base64,XXXX → media_type と data に分解
            if "," not in data_url:
                continue
            header, b64data = data_url.split(",", 1)
            media_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
            image_blocks.append({
                "label": f"{label}の示唆画像{i}",
                "media_type": media_type,
                "data": b64data,
            })

    return text, image_blocks

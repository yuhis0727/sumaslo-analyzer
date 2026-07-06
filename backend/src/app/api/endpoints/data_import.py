"""
データインポートエンドポイント
ローカルスクレイパーが毎日の台データをPOSTする口

POST /api/data/import
  body: { "date": "2026-07-05", "machines": [...] }
  認証: X-Import-Token ヘッダー（.envのIMPORT_TOKEN）
"""
from __future__ import annotations

import os
from datetime import date as date_type
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.app.models import SessionLocal, engine
from src.app.models.slot_data import Machine, Store

router = APIRouter()

STORE_NAME = "マルハン蒲田7"


def _get_store_id() -> int:
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.name == STORE_NAME).first()
        if not store:
            raise HTTPException(status_code=500, detail=f"Store '{STORE_NAME}' が見つかりません")
        return store.id
    finally:
        db.close()


def _verify_token(x_import_token: str | None) -> None:
    expected = os.getenv("IMPORT_TOKEN", "")
    if not expected:
        return  # 未設定なら認証スキップ（ローカル開発用）
    if x_import_token != expected:
        raise HTTPException(status_code=401, detail="Invalid import token")


class MachineRow(BaseModel):
    machine_number: int
    model_name: str
    total_diff: int | None = None
    game_count: int | None = None


class ImportRequest(BaseModel):
    date: date_type
    machines: list[MachineRow]


@router.post("/data/import")
def import_machines(
    req: ImportRequest,
    x_import_token: str | None = Header(default=None),
):
    """日次台データをDBにupsertする"""
    _verify_token(x_import_token)

    if not req.machines:
        raise HTTPException(status_code=400, detail="machines が空です")

    store_id = _get_store_id()
    now = datetime.now()

    records = [
        {
            "store_id": store_id,
            "machine_number": m.machine_number,
            "model_name": m.model_name,
            "date": req.date,
            "diff_medals": m.total_diff,
            "games_played": m.game_count,
            "created_at": now,
        }
        for m in req.machines
    ]

    stmt = pg_insert(Machine.__table__).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "machine_number", "date"],
        set_={
            "model_name": stmt.excluded.model_name,
            "diff_medals": stmt.excluded.diff_medals,
            "games_played": stmt.excluded.games_played,
        },
    )

    with engine.connect() as conn:
        result = conn.execute(stmt)
        conn.commit()

    # CSVキャッシュをクリアして次回アクセス時に再読み込み
    try:
        from src.app.api.endpoints.csv_data import _load_df
        _load_df.cache_clear()
    except Exception:
        pass

    return {
        "date": req.date.isoformat(),
        "upserted": len(records),
        "store_id": store_id,
    }

"""スロット分析 API (CLAUDE.md 仕様準拠)

GET  /api/stores                     店舗一覧
POST /api/stores                     店舗登録
GET  /api/stores/{id}                店舗詳細
GET  /api/stores/{id}/machines       台データ一覧
GET  /api/stores/{id}/predictions    予測結果
GET  /api/predictions/top            全店舗の高設定候補TOP N
GET  /api/models/{name}/theoretical  機種別理論値
POST /api/scrape/trigger             手動スクレイピング実行
GET  /api/stats/accuracy             予測精度の統計
"""

import json
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.app.models import get_db
from src.app.models.slot_data import (
    Machine,
    Prediction,
    ScrapingLog,
    Store,
    TheoreticalValue,
)
from src.app.services.scraper import AnasloScraper

router = APIRouter()


# ──────────────────────────────────────────
# Pydantic スキーマ
# ──────────────────────────────────────────


class StoreCreate(BaseModel):
    name: str = Field(..., description="店舗名")
    address: str | None = Field(None, description="住所")
    prefecture: str | None = Field(None, description="都道府県")
    url: str = Field(..., description="アナスロ データ一覧ページ URL")


class StoreResponse(BaseModel):
    id: int
    name: str
    address: str | None
    prefecture: str | None
    url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class MachineResponse(BaseModel):
    id: int
    store_id: int
    machine_number: int
    model_name: str
    date: date
    games_played: int | None
    diff_medals: int | None
    bonus_count: int | None
    reg_count: int | None
    big_count: int | None
    at_count: int | None

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id: int
    store_id: int
    machine_number: int
    model_name: str
    date: date
    prediction_score: float
    predicted_setting: int | None
    confidence: float

    class Config:
        from_attributes = True


class TheoreticalValueResponse(BaseModel):
    id: int
    model_name: str
    setting: int
    reg_prob: float | None
    big_prob: float | None
    at_rate: float | None
    diff_rate_per_game: float | None
    source_url: str | None

    class Config:
        from_attributes = True


class TheoreticalValueCreate(BaseModel):
    setting: int = Field(..., ge=1, le=6)
    reg_prob: float | None = None
    big_prob: float | None = None
    at_rate: float | None = None
    diff_rate_per_game: float | None = None
    source_url: str | None = None


class ScrapeRequest(BaseModel):
    store_id: int
    target_date: str = Field(..., description="取得対象日付 (例: 2026/01/14)")


# ──────────────────────────────────────────
# 店舗 API
# ──────────────────────────────────────────


@router.post("/stores", response_model=StoreResponse, status_code=201)
async def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    """店舗を登録"""
    db_store = Store(
        name=store.name,
        address=store.address,
        prefecture=store.prefecture,
        url=store.url,
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/stores", response_model=list[StoreResponse])
async def list_stores(
    prefecture: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """店舗一覧を取得"""
    q = db.query(Store)
    if prefecture:
        q = q.filter(Store.prefecture == prefecture)
    return q.offset(skip).limit(limit).all()


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    """特定の店舗を取得"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")
    return store


# ──────────────────────────────────────────
# 台データ API
# ──────────────────────────────────────────


@router.get("/stores/{store_id}/machines", response_model=list[MachineResponse])
async def list_machines(
    store_id: int,
    date: date | None = None,
    model_name: str | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """台データ一覧を取得"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    q = db.query(Machine).filter(Machine.store_id == store_id)
    if date:
        q = q.filter(Machine.date == date)
    if model_name:
        q = q.filter(Machine.model_name == model_name)

    return (
        q.order_by(Machine.date.desc(), Machine.machine_number)
        .offset(skip)
        .limit(limit)
        .all()
    )


# ──────────────────────────────────────────
# 予測 API
# ──────────────────────────────────────────


@router.get("/stores/{store_id}/predictions", response_model=list[PredictionResponse])
async def list_predictions(
    store_id: int,
    date: date | None = None,
    min_score: float = 0.0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """店舗の予測結果を取得"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    q = db.query(Prediction).filter(
        Prediction.store_id == store_id,
        Prediction.prediction_score >= min_score,
    )
    if date:
        q = q.filter(Prediction.date == date)

    return (
        q.order_by(Prediction.prediction_score.desc())
        .limit(limit)
        .all()
    )


@router.get("/predictions/top")
async def top_predictions(
    target_date: date | None = None,
    min_score: float = Query(default=0.7, description="最低スコア閾値"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """全店舗の高設定候補TOP Nを返す

    CLAUDE.md 実戦ルール: スコア 0.7 以上のみ表示
    """
    q = db.query(Prediction, Store).join(
        Store, Prediction.store_id == Store.id
    ).filter(Prediction.prediction_score >= min_score)

    if target_date:
        q = q.filter(Prediction.date == target_date)

    rows = (
        q.order_by(Prediction.prediction_score.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "store_id": pred.store_id,
            "store_name": store.name,
            "prefecture": store.prefecture,
            "machine_number": pred.machine_number,
            "model_name": pred.model_name,
            "date": pred.date.isoformat(),
            "prediction_score": pred.prediction_score,
            "predicted_setting": pred.predicted_setting,
            "confidence": pred.confidence,
        }
        for pred, store in rows
    ]


# ──────────────────────────────────────────
# 理論値 API
# ──────────────────────────────────────────


@router.get(
    "/models/{model_name}/theoretical",
    response_model=list[TheoreticalValueResponse],
)
async def get_theoretical_values(
    model_name: str,
    setting: int | None = None,
    db: Session = Depends(get_db),
):
    """機種別理論値を取得 (設定1〜6)"""
    q = db.query(TheoreticalValue).filter(
        TheoreticalValue.model_name == model_name
    )
    if setting is not None:
        q = q.filter(TheoreticalValue.setting == setting)
    rows = q.order_by(TheoreticalValue.setting).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"理論値が見つかりません: {model_name}")
    return rows


@router.post("/models/{model_name}/theoretical", status_code=201)
async def upsert_theoretical_value(
    model_name: str,
    body: TheoreticalValueCreate,
    db: Session = Depends(get_db),
):
    """機種の設定別理論値を登録・更新"""
    existing = (
        db.query(TheoreticalValue)
        .filter(
            TheoreticalValue.model_name == model_name,
            TheoreticalValue.setting == body.setting,
        )
        .first()
    )
    if existing:
        existing.reg_prob = body.reg_prob
        existing.big_prob = body.big_prob
        existing.at_rate = body.at_rate
        existing.diff_rate_per_game = body.diff_rate_per_game
        existing.source_url = body.source_url
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_tv = TheoreticalValue(
            model_name=model_name,
            setting=body.setting,
            reg_prob=body.reg_prob,
            big_prob=body.big_prob,
            at_rate=body.at_rate,
            diff_rate_per_game=body.diff_rate_per_game,
            source_url=body.source_url,
        )
        db.add(new_tv)
        db.commit()
        db.refresh(new_tv)
        return new_tv


# ──────────────────────────────────────────
# スクレイピング API
# ──────────────────────────────────────────


@router.post("/scrape/trigger")
async def trigger_scrape(
    body: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手動スクレイピングを実行する

    アクセス間隔: 最低 2.5 秒を確保 (CLAUDE.md 規約)
    """
    store = db.query(Store).filter(Store.id == body.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")
    if not store.url:
        raise HTTPException(status_code=400, detail="店舗にアナスロURLが設定されていません")

    log = ScrapingLog(
        store_id=body.store_id,
        status="running",
        started_at=datetime.now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    background_tasks.add_task(
        _execute_scraping, body.store_id, store.url, body.target_date, log.id
    )

    return {
        "message": "スクレイピングを開始しました",
        "store_id": body.store_id,
        "target_date": body.target_date,
        "log_id": log.id,
    }


def _execute_scraping(
    store_id: int, url: str, target_date: str, log_id: int
) -> None:
    """バックグラウンドスクレイピング処理"""
    from src.app.models import SessionLocal

    db: Session = SessionLocal()
    log = db.query(ScrapingLog).filter(ScrapingLog.id == log_id).first()

    try:
        # アクセス間隔を確保 (CLAUDE.md: 最低 2〜3 秒)
        scraper = AnasloScraper(headless=True)
        data = scraper.scrape_store_data_by_date(
            list_url=url,
            target_date=target_date,
        )

        scraped_date = datetime.strptime(
            target_date.replace("/", "-"), "%Y-%m-%d"
        ).date()

        for machine in data.get("machines", []):
            if machine.get("machine_number") is None:
                continue
            db_machine = Machine(
                store_id=store_id,
                machine_number=machine["machine_number"],
                model_name=machine.get("model_name", "不明"),
                date=scraped_date,
                games_played=machine.get("game_count"),
                diff_medals=machine.get("total_difference"),
                bonus_count=(
                    (machine.get("big_bonus") or 0)
                    + (machine.get("regular_bonus") or 0)
                ),
                reg_count=machine.get("regular_bonus"),
                big_count=machine.get("big_bonus"),
                at_count=machine.get("art_count"),
            )
            db.add(db_machine)

        if log:
            log.status = "success"
            log.scraped_count = len(data.get("machines", []))
            log.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        if log:
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.now()
        db.commit()
    finally:
        db.close()


@router.get("/scrape/logs/{store_id}")
async def get_scraping_logs(
    store_id: int, limit: int = 10, db: Session = Depends(get_db)
):
    """スクレイピングログを取得"""
    logs = (
        db.query(ScrapingLog)
        .filter(ScrapingLog.store_id == store_id)
        .order_by(ScrapingLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return logs


# ──────────────────────────────────────────
# 統計 API
# ──────────────────────────────────────────


@router.get("/stats/accuracy")
async def get_accuracy_stats(
    store_id: int | None = None,
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db),
):
    """予測精度の統計を返す

    prediction_score >= 0.7 の台が実際に高差枚 (diff_medals > 2000) だった割合を計算。
    """
    from datetime import timedelta

    cutoff = date.today() - timedelta(days=days)

    pred_q = db.query(Prediction).filter(
        Prediction.date >= cutoff,
        Prediction.prediction_score >= 0.7,
    )
    if store_id:
        pred_q = pred_q.filter(Prediction.store_id == store_id)

    predictions = pred_q.all()

    if not predictions:
        return {
            "total_predictions": 0,
            "high_setting_hits": 0,
            "precision": None,
            "period_days": days,
        }

    hits = 0
    for pred in predictions:
        actual = (
            db.query(Machine)
            .filter(
                Machine.store_id == pred.store_id,
                Machine.machine_number == pred.machine_number,
                Machine.date == pred.date,
            )
            .first()
        )
        # 差枚数 2000 枚以上を「高設定実績あり」とみなす
        if actual and actual.diff_medals is not None and actual.diff_medals >= 2000:
            hits += 1

    precision = hits / len(predictions) if predictions else 0.0

    return {
        "total_predictions": len(predictions),
        "high_setting_hits": hits,
        "precision": round(precision, 4),
        "period_days": days,
    }

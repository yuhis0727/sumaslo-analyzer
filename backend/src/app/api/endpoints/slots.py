from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.app.models import get_db
from src.app.models.slot_data import Store, SlotMachine, Prediction, ScrapingLog
from src.app.services.scraper import AnasloScraper
from src.app.services.ai_analyzer import SlotAIAnalyzer

router = APIRouter()


# Pydantic スキーマ
class StoreCreate(BaseModel):
    name: str = Field(..., description="店舗名")
    area: Optional[str] = Field(None, description="エリア")
    anaslo_url: str = Field(..., description="アナスロのURL")


class StoreResponse(BaseModel):
    id: int
    name: str
    area: Optional[str]
    anaslo_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MachineData(BaseModel):
    machine_number: int
    model_name: str
    game_count: Optional[int]
    big_bonus: Optional[int]
    regular_bonus: Optional[int]
    art_count: Optional[int]
    total_difference: Optional[int]


class PredictionResponse(BaseModel):
    id: int
    store_id: int
    prediction_date: datetime
    high_setting_probability: float
    confidence_score: float
    recommended_machines: Optional[str]
    analysis_details: Optional[str]

    class Config:
        from_attributes = True


class AnalysisResult(BaseModel):
    store_name: str
    high_setting_probability: float
    confidence_score: float
    recommended_machines: List[int]
    analysis_details: dict


# エンドポイント
@router.post("/stores", response_model=StoreResponse)
async def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    """店舗を登録"""
    db_store = Store(
        name=store.name, area=store.area, anaslo_url=store.anaslo_url
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/stores", response_model=List[StoreResponse])
async def get_stores(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """店舗一覧を取得"""
    stores = db.query(Store).offset(skip).limit(limit).all()
    return stores


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    """特定の店舗を取得"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")
    return store


@router.post("/scrape/{store_id}")
async def scrape_store_data(
    store_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """店舗データをスクレイピング"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    # バックグラウンドでスクレイピング実行
    background_tasks.add_task(execute_scraping, store_id, store.anaslo_url, db)

    return {"message": "スクレイピングを開始しました", "store_id": store_id}


async def execute_scraping(store_id: int, url: str, db: Session):
    """スクレイピング実行(バックグラウンド処理)"""
    log = ScrapingLog(
        store_id=store_id, status="running", started_at=datetime.now()
    )
    db.add(log)
    db.commit()

    try:
        scraper = AnasloScraper(headless=True)
        data = scraper.scrape_store_data(url)

        # 台データを保存
        for machine in data["machines"]:
            db_machine = SlotMachine(
                store_id=store_id,
                machine_number=machine["machine_number"],
                model_name=machine["model_name"],
                game_count=machine.get("game_count"),
                big_bonus=machine.get("big_bonus"),
                regular_bonus=machine.get("regular_bonus"),
                art_count=machine.get("art_count"),
                total_difference=machine.get("total_difference"),
                data_date=data["data_date"],
            )
            db.add(db_machine)

        log.status = "success"
        log.scraped_count = len(data["machines"])
        log.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.completed_at = datetime.now()
        db.commit()


@router.post("/analyze/{store_id}", response_model=AnalysisResult)
async def analyze_store(store_id: int, db: Session = Depends(get_db)):
    """店舗データを分析"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    # 最新の台データを取得
    machines = (
        db.query(SlotMachine)
        .filter(SlotMachine.store_id == store_id)
        .order_by(SlotMachine.data_date.desc())
        .limit(100)
        .all()
    )

    if not machines:
        raise HTTPException(status_code=404, detail="分析対象のデータがありません")

    # 台データを辞書形式に変換
    machines_data = [
        {
            "machine_number": m.machine_number,
            "model_name": m.model_name,
            "game_count": m.game_count,
            "big_bonus": m.big_bonus,
            "regular_bonus": m.regular_bonus,
            "art_count": m.art_count,
            "total_difference": m.total_difference,
        }
        for m in machines
    ]

    # AI分析実行
    analyzer = SlotAIAnalyzer()
    result = analyzer.analyze_store({"machines": machines_data})

    # 予測結果を保存
    prediction = Prediction(
        store_id=store_id,
        prediction_date=datetime.now(),
        high_setting_probability=result["high_setting_probability"],
        confidence_score=result["confidence_score"],
        recommended_machines=str(result["recommended_machines"]),
        analysis_details=str(result["analysis_details"]),
    )
    db.add(prediction)
    db.commit()

    return AnalysisResult(
        store_name=store.name,
        high_setting_probability=result["high_setting_probability"],
        confidence_score=result["confidence_score"],
        recommended_machines=result["recommended_machines"],
        analysis_details=result["analysis_details"],
    )


@router.get("/predictions/{store_id}", response_model=List[PredictionResponse])
async def get_predictions(
    store_id: int, limit: int = 10, db: Session = Depends(get_db)
):
    """店舗の予測履歴を取得"""
    predictions = (
        db.query(Prediction)
        .filter(Prediction.store_id == store_id)
        .order_by(Prediction.prediction_date.desc())
        .limit(limit)
        .all()
    )
    return predictions


@router.get("/scraping-logs/{store_id}")
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

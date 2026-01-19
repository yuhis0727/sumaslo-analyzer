from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.app.models import get_db
from src.app.models.slot_data import Prediction, ScrapingLog, SlotMachine, Store
from src.app.services.ai_analyzer import SlotAIAnalyzer
from src.app.services.analysis_service import AnalysisService
from src.app.services.data_service import DataService
from src.app.services.scraper import AnasloScraper

router = APIRouter()


# Pydantic スキーマ
class StoreCreate(BaseModel):
    name: str = Field(..., description="店舗名")
    area: str | None = Field(None, description="エリア")
    anaslo_url: str = Field(..., description="アナスロのURL")


class StoreResponse(BaseModel):
    id: int
    name: str
    area: str | None
    anaslo_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class MachineData(BaseModel):
    machine_number: int
    model_name: str
    game_count: int | None
    big_bonus: int | None
    regular_bonus: int | None
    art_count: int | None
    total_difference: int | None


class PredictionResponse(BaseModel):
    id: int
    store_id: int
    prediction_date: datetime
    high_setting_probability: float
    confidence_score: float
    recommended_machines: str | None
    analysis_details: str | None

    class Config:
        from_attributes = True


class AnalysisResult(BaseModel):
    store_name: str
    high_setting_probability: float
    confidence_score: float
    recommended_machines: list[int]
    analysis_details: dict


# エンドポイント
@router.post("/stores", response_model=StoreResponse)
async def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    """店舗を登録"""
    db_store = Store(
        name=store.name, area=store.area, anaslo_url=store.anaslo_url,
    )
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.get("/stores", response_model=list[StoreResponse])
async def get_stores(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
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
    store_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db),
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
        store_id=store_id, status="running", started_at=datetime.now(),
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


@router.get("/predictions/{store_id}", response_model=list[PredictionResponse])
async def get_predictions(
    store_id: int, limit: int = 10, db: Session = Depends(get_db),
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
    store_id: int, limit: int = 10, db: Session = Depends(get_db),
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


# ===================
# 新しい分析エンドポイント
# ===================


@router.get("/recommendations/{store_id}")
async def get_recommendations(
    store_id: int,
    history_days: int = Query(30, ge=7, le=90, description="分析に使う過去日数"),
    top_n: int = Query(10, ge=1, le=50, description="推奨台数"),
    db: Session = Depends(get_db),
):
    """座るべき台を推奨（新分析ロジック）"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    analysis_service = AnalysisService(db)
    result = analysis_service.get_recommended_machines(
        store_id=store_id,
        history_days=history_days,
        top_n=top_n,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/machines/{store_id}/{machine_number}")
async def get_machine_detail(
    store_id: int,
    machine_number: int,
    history_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """特定の台番号の詳細分析"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    analysis_service = AnalysisService(db)
    result = analysis_service.get_machine_detail(
        store_id=store_id,
        machine_number=machine_number,
        history_days=history_days,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/scrape-by-date/{store_id}")
async def scrape_store_data_by_date(
    store_id: int,
    target_date: str = Query(..., description="取得日付（例: 2026/01/14）"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """日付指定でデータをスクレイピング（Cloudflare対応）"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    if not store.anaslo_url:
        raise HTTPException(status_code=400, detail="店舗のURLが設定されていません")

    # バックグラウンドでスクレイピング実行
    background_tasks.add_task(
        execute_scraping_by_date, store_id, store.anaslo_url, target_date, db
    )

    return {
        "message": "スクレイピングを開始しました",
        "store_id": store_id,
        "target_date": target_date,
    }


async def execute_scraping_by_date(
    store_id: int, list_url: str, target_date: str, db: Session
):
    """日付指定スクレイピング実行（バックグラウンド処理）"""
    data_service = DataService(db)
    log = data_service.create_scraping_log(store_id=store_id, status="running")

    try:
        scraper = AnasloScraper(headless=False)
        data = scraper.scrape_store_data_by_date(list_url, target_date)

        # 日付をパース
        data_date = datetime.strptime(target_date, "%Y/%m/%d").date()

        # データを保存
        saved_count = data_service.save_scraped_data(data, data_date)

        # 集計を実行
        data_service.run_all_aggregations(store_id, data_date)

        data_service.update_scraping_log(
            log, status="success", scraped_count=saved_count
        )

    except Exception as e:
        data_service.update_scraping_log(
            log, status="failed", error_message=str(e)
        )


@router.post("/aggregate/{store_id}")
async def run_aggregation(
    store_id: int,
    data_date: date = Query(..., description="集計対象日"),
    history_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """手動で集計を実行"""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="店舗が見つかりません")

    data_service = DataService(db)
    result = data_service.run_all_aggregations(store_id, data_date, history_days)

    return {
        "message": "集計が完了しました",
        "store_id": store_id,
        "data_date": data_date.isoformat(),
        "store_summary": result["store_summary"] is not None,
        "model_summaries_count": len(result["model_summaries"]),
        "position_histories_count": len(result["position_histories"]),
    }

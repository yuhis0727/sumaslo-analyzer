from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.endpoints.health_check import health_check
from src.app.api.endpoints.slots import router as slots_router
from src.app.api.endpoints.csv_data import router as csv_router
from src.app.api.endpoints.ai_chat import router as ai_router
from src.app.api.endpoints.simulator import router as simulator_router
from src.app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリ起動・終了時の処理"""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Sumaslo Analyzer",
    description="スマスロデータ分析・AI予測システム",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://sumaslo-analyzer.dev",
        "https://sumaslo-analyzer.dev",
        "http://localhost",
        "https://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# エンドポイントのルーティング
app.include_router(health_check, prefix="/_health")
app.include_router(slots_router, prefix="/api", tags=["slots"])
app.include_router(csv_router, prefix="/api", tags=["csv-data"])
app.include_router(ai_router, prefix="/api", tags=["ai"])
app.include_router(simulator_router, prefix="/api", tags=["simulator"])

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.app.api.endpoints.ai_chat import router as ai_router
from src.app.api.endpoints.csv_data import router as csv_router
from src.app.api.endpoints.health_check import health_check
from src.app.api.endpoints.hints import router as hints_router
from src.app.api.endpoints.predictions import router as predictions_router
from src.app.api.endpoints.simulator import router as simulator_router
from src.app.stores import store_middleware

app = FastAPI(
    title="Sumaslo Analyzer",
    description="スマスロデータ分析・AI予測システム",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# 店舗切替ミドルウェア（?store= / X-Store ヘッダで店舗を解決）
app.middleware("http")(store_middleware)

# エンドポイントのルーティング
app.include_router(health_check, prefix="/_health")
app.include_router(csv_router, prefix="/api", tags=["csv-data"])
app.include_router(ai_router, prefix="/api", tags=["ai"])
app.include_router(simulator_router, prefix="/api", tags=["simulator"])
app.include_router(hints_router, prefix="/api", tags=["hints"])
app.include_router(predictions_router, prefix="/api", tags=["predictions"])

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from src.app.api.endpoints.health_check import health_check
from src.app.api.endpoints.slots import router as slots_router

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# カスタムエラーハンドラーの設定

# 必要なら使う
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request,
#                                        exc: RequestValidationError):
#     errors = [err['msg'].replace("Value error, ", "")
#               for err in exc.errors()]

#     return JSONResponse(
#         status_code=HTTP_422_UNPROCESSABLE_ENTITY,
#         content={"error_messages": errors},
#     )


# エンドポイントのルーティングを追加
app.include_router(health_check, prefix="/_health")
app.include_router(slots_router, prefix="/api/v1/slots", tags=["slots"])

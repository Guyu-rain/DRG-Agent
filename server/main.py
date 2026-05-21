"""DRG-Agent FastAPI 应用入口。

启动: cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_models
from app.core.logging import logger, setup_logging
from app.core.middleware import register_exception_handlers, register_middleware
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期: 启动时初始化日志与数据库表。"""
    setup_logging()
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        await init_models()
        logger.info("数据库表已就绪")
    except Exception as exc:  # noqa: BLE001 - 数据库不可用时仍允许应用启动
        logger.error(f"数据库初始化失败 (请检查 PostgreSQL 容器): {exc}")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title="DRG-Agent",
    description="医保 DRG 入组智能体系统 —— 后端 API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "code": 200,
        "data": {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"},
        "message": "DRG-Agent API is running",
    }

"""HTTP 中间件与全局异常处理。"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的方法、路径、状态码与耗时。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 - 交由异常处理器统一返回
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(f"{request.method} {request.url.path} -> 异常 ({elapsed:.1f}ms)")
            raise
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.1f}ms)")
        return response


def _envelope(code: int, message: str, detail: dict | None = None) -> dict:
    body: dict = {"code": code, "data": None, "message": message}
    if detail is not None:
        body["detail"] = detail
    return body


def register_middleware(app: FastAPI) -> None:
    """注册 CORS、请求日志中间件。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，统一返回 {code, data, message} 结构。"""

    @app.exception_handler(AppException)
    async def _app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(422, "请求数据校验失败", {"errors": exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"未处理的异常: {exc}")
        return JSONResponse(status_code=500, content=_envelope(500, "服务器内部错误"))

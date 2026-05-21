"""API 依赖注入。"""

from __future__ import annotations

from fastapi import Query

from app.core.database import get_db

__all__ = ["get_db", "pagination_params"]


def pagination_params(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=200, alias="pageSize", description="每页数量"),
) -> dict:
    """统一分页查询参数。"""
    return {"page": page, "page_size": page_size}

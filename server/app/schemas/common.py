"""通用 Pydantic 模型: 统一响应格式、分页。"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """对外字段使用 camelCase 别名, 同时允许以 snake_case 赋值。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class APIResponse(BaseModel, Generic[T]):
    """统一响应包装 (参照 plans/03_api_interfaces.md §1.3)。"""

    code: int = 200
    data: T | None = None
    message: str = "success"


class PaginationParams(CamelModel):
    """分页查询参数。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class PaginationData(CamelModel, Generic[T]):
    """分页数据体。"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def ok(data: object = None, message: str = "success", code: int = 200) -> dict:
    """构造成功响应字典。"""
    return {"code": code, "data": data, "message": message}


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    """构造分页数据字典 (camelCase)。"""
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
    }

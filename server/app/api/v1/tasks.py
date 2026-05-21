"""任务中心 API。参照 plans/03_api_interfaces.md §7。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.schemas.common import ok, paginate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["任务中心"])


@router.get("", summary="获取任务列表")
async def list_tasks(
    page_params: dict = Depends(pagination_params),
    type: str = Query(default="all"),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TaskService(db)
    items, total = await service.get_tasks(task_type=type, status=status, **page_params)
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))


@router.get("/{task_id}", summary="获取任务详情")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = TaskService(db)
    return ok(await service.get_task_detail(task_id))


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = TaskService(db)
    return ok(await service.cancel_task(task_id), message="任务已取消")

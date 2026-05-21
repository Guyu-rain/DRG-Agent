"""智能体执行日志 API。参照 plans/03_api_interfaces.md §9。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.models import ExecutionLog
from app.schemas.common import ok

router = APIRouter(prefix="/logs", tags=["执行日志"])


@router.get("", summary="获取执行日志")
async def list_logs(
    page_params: dict = Depends(pagination_params),
    task_id: str | None = Query(default=None, alias="taskId"),
    level: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(ExecutionLog)
    count_stmt = select(func.count()).select_from(ExecutionLog)
    if task_id:
        stmt = stmt.where(ExecutionLog.task_id == task_id)
        count_stmt = count_stmt.where(ExecutionLog.task_id == task_id)
    if level:
        stmt = stmt.where(ExecutionLog.level == level)
        count_stmt = count_stmt.where(ExecutionLog.level == level)

    total = (await db.execute(count_stmt)).scalar_one()
    page, page_size = page_params["page"], page_params["page_size"]
    stmt = stmt.order_by(ExecutionLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        {
            "logId": log.id,
            "timestamp": log.timestamp,
            "level": log.level,
            "agent": log.agent,
            "taskId": log.task_id,
            "message": log.message,
            "inputSummary": log.input_summary,
            "outputSummary": log.output_summary,
            "errorDetail": log.error_detail,
        }
        for log in rows
    ]
    return ok({"items": items, "total": total})

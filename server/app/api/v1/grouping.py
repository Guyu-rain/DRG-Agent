"""DRG 入组 API。参照 plans/03_api_interfaces.md §4。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.schemas.common import ok, paginate
from app.schemas.grouping import BatchGroupingRequest, GroupingExecuteRequest
from app.services.grouping_service import GroupingService

router = APIRouter(prefix="/grouping", tags=["DRG 入组"])


@router.post("/execute", status_code=202, summary="执行入组")
async def execute_grouping(payload: GroupingExecuteRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = GroupingService(db)
    task = await service.execute_grouping(payload.case_id, payload.rule_version_id)
    return ok(
        {"taskId": task.id, "status": task.status, "startedAt": task.started_at},
        message="入组任务已执行",
        code=202,
    )


@router.post("/batch", status_code=202, summary="批量入组")
async def batch_grouping(payload: BatchGroupingRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = GroupingService(db)
    tasks = await service.batch_grouping(payload.case_ids, payload.rule_version_id)
    return ok(
        {
            "batchTaskId": tasks[0].id if tasks else None,
            "totalCases": len(payload.case_ids),
            "status": "completed",
            "taskIds": [t.id for t in tasks],
        },
        message="批量入组已完成",
        code=202,
    )


@router.get("/results/{task_id}", summary="查询入组结果")
async def get_grouping_result(task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = GroupingService(db)
    return ok(await service.get_grouping_result(task_id))


@router.get("/tasks", summary="查询入组任务列表")
async def list_grouping_tasks(
    page_params: dict = Depends(pagination_params),
    status: str | None = Query(default=None),
    case_id: str | None = Query(default=None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = GroupingService(db)
    tasks, total = await service.get_tasks(status=status, case_id=case_id, **page_params)
    items = [service.to_task_summary(t) for t in tasks]
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))

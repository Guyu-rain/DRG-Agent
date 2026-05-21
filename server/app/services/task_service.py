"""任务中心服务层。参照 plans/03_api_interfaces.md §7。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCode, NotFoundException
from app.models import DocumentTask, GroupingTask, TaskStep, TestTask


class TaskService:
    """统一聚合入组 / 文档生成 / 测试生成任务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_tasks(
        self, page: int = 1, page_size: int = 20, task_type: str = "all", status: str | None = None
    ) -> tuple[list[dict], int]:
        items: list[dict] = []

        if task_type in ("all", "grouping"):
            rows = (await self.db.execute(select(GroupingTask))).scalars().all()
            items.extend(
                {
                    "taskId": t.id, "type": "grouping", "status": t.status,
                    "createdAt": t.created_at, "finishedAt": t.finished_at,
                }
                for t in rows
            )
        if task_type in ("all", "document_gen"):
            rows = (await self.db.execute(select(DocumentTask))).scalars().all()
            items.extend(
                {
                    "taskId": t.id, "type": "document_gen", "status": t.status,
                    "createdAt": t.created_at, "finishedAt": t.finished_at,
                }
                for t in rows
            )
        if task_type in ("all", "test_gen"):
            rows = (await self.db.execute(select(TestTask))).scalars().all()
            items.extend(
                {
                    "taskId": t.id, "type": "test_gen", "status": t.status,
                    "createdAt": t.created_at, "finishedAt": t.finished_at,
                }
                for t in rows
            )

        if status:
            items = [it for it in items if it["status"] == status]
        items.sort(key=lambda it: it["createdAt"] or "", reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def get_task_detail(self, task_id: str) -> dict:
        """获取任务详情。入组任务额外返回执行步骤。"""
        grouping = await self.db.get(GroupingTask, task_id)
        if grouping is not None:
            steps = (
                await self.db.execute(
                    select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_order)
                )
            ).scalars().all()
            return {
                "taskId": grouping.id, "type": "grouping", "status": grouping.status,
                "startedAt": grouping.started_at, "finishedAt": grouping.finished_at,
                "durationMs": grouping.duration_ms,
                "steps": [
                    {"step": s.step_name, "status": s.status, "durationMs": s.duration_ms}
                    for s in steps
                ],
                "error": (
                    {"type": grouping.error_type, "message": grouping.error_message}
                    if grouping.error_type
                    else None
                ),
            }

        doc = await self.db.get(DocumentTask, task_id)
        if doc is not None:
            return {
                "taskId": doc.id, "type": "document_gen", "status": doc.status,
                "startedAt": doc.started_at, "finishedAt": doc.finished_at, "steps": [],
                "error": {"message": doc.error_message} if doc.error_message else None,
            }

        test = await self.db.get(TestTask, task_id)
        if test is not None:
            return {
                "taskId": test.id, "type": "test_gen", "status": test.status,
                "startedAt": test.started_at, "finishedAt": test.finished_at, "steps": [],
                "error": {"message": test.error_message} if test.error_message else None,
            }

        raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"任务不存在: {task_id}")

    async def cancel_task(self, task_id: str) -> dict:
        """取消任务 (仅对未完成的任务有效)。"""
        for model in (GroupingTask, DocumentTask, TestTask):
            task = await self.db.get(model, task_id)
            if task is not None:
                if task.status in ("pending", "executing", "running"):
                    task.status = "cancelled"
                    await self.db.flush()
                return {"taskId": task_id, "status": task.status}
        raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"任务不存在: {task_id}")

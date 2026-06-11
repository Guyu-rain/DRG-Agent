"""任务中心服务层。参照 plans/03_api_interfaces.md §7。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCode, NotFoundException
from app.models import DocumentTask, GroupingTask, TaskStep, TestTask


def _duration_ms(started: datetime | None, finished: datetime | None) -> int | None:
    """根据起止时间计算耗时 (毫秒)。"""
    if started and finished:
        return int((finished - started).total_seconds() * 1000)
    return None


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
                    "taskId": t.id,
                    "type": "grouping",
                    "title": f"DRG 入组 · {(t.input_snapshot or {}).get('primaryDiagnosis') or t.case_id}",
                    "status": t.status,
                    "createdAt": t.created_at,
                    "finishedAt": t.finished_at,
                    "durationMs": t.duration_ms,
                }
                for t in rows
            )
        if task_type in ("all", "document_gen"):
            rows = (await self.db.execute(select(DocumentTask))).scalars().all()
            items.extend(
                {
                    "taskId": t.id,
                    "type": "document",
                    "title": f"文档生成 · {t.title}",
                    "status": t.status,
                    "createdAt": t.created_at,
                    "finishedAt": t.finished_at,
                    "durationMs": _duration_ms(t.started_at, t.finished_at),
                }
                for t in rows
            )
        if task_type in ("all", "test_gen"):
            rows = (await self.db.execute(select(TestTask))).scalars().all()
            items.extend(
                {
                    "taskId": t.id,
                    "type": "testcase",
                    "title": f"测试用例生成 · {t.generated_count or 0} 条",
                    "status": t.status,
                    "createdAt": t.created_at,
                    "finishedAt": t.finished_at,
                    "durationMs": _duration_ms(t.started_at, t.finished_at),
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
                "taskId": grouping.id,
                "type": "grouping",
                "title": f"DRG 入组 · {(grouping.input_snapshot or {}).get('primaryDiagnosis') or grouping.case_id}",
                "status": grouping.status,
                "startedAt": grouping.started_at,
                "finishedAt": grouping.finished_at,
                "durationMs": grouping.duration_ms,
                "steps": [
                    {
                        "stepName": s.step_name,
                        "stepOrder": s.step_order,
                        "status": s.status,
                        "durationMs": s.duration_ms,
                        "inputSummary": s.input_summary,
                        "outputSummary": s.output_summary,
                        "errorMessage": s.error_message,
                    }
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
                "taskId": doc.id,
                "type": "document",
                "title": f"文档生成 · {doc.title}",
                "status": doc.status,
                "startedAt": doc.started_at,
                "finishedAt": doc.finished_at,
                "durationMs": _duration_ms(doc.started_at, doc.finished_at),
                "steps": [],
                "error": {"message": doc.error_message} if doc.error_message else None,
            }

        test = await self.db.get(TestTask, task_id)
        if test is not None:
            return {
                "taskId": test.id,
                "type": "testcase",
                "title": f"测试用例生成 · {test.generated_count or 0} 条",
                "status": test.status,
                "startedAt": test.started_at,
                "finishedAt": test.finished_at,
                "durationMs": _duration_ms(test.started_at, test.finished_at),
                "steps": [],
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

    async def submit_for_review(self, task_id: str) -> dict:
        """提交分组任务复核 (将 completed 状态改为 needs_review)。"""
        task = await self.db.get(GroupingTask, task_id)
        if task is None:
            raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"分组任务不存在: {task_id}")
        if task.status != "completed":
            raise BadRequestException(ErrorCode.RESOURCE_IN_USE, "仅已完成的任务可提交复核")
        task.status = "needs_review"
        await self.db.flush()
        return {"taskId": task_id, "status": task.status}

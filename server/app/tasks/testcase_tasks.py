"""测试用例生成相关 Celery 任务。参照 plans/phase1_backend.md §8。"""

from __future__ import annotations

from app.core.logging import logger
from app.tasks import celery_app
from app.tasks.async_runner import run_async


async def _generate(test_task_id: str) -> str:
    from app.core.database import async_session
    from app.models import TestTask
    from app.services.testcase_service import TestCaseService

    async with async_session() as db:
        task = await db.get(TestTask, test_task_id)
        if task is None:
            logger.error(f"测试任务不存在: {test_task_id}")
            return "missing"
        if task.status == "cancelled":
            logger.info(f"测试任务已取消，跳过执行: {test_task_id}")
            return "cancelled"
        try:
            await TestCaseService(db).run_generation(task)
            await db.commit()
            return task.status
        except Exception:  # noqa: BLE001
            await db.commit()
            raise


@celery_app.task(name="testcase.generate", bind=True, max_retries=2)
def generate_testcases_task(self, test_task_id: str) -> dict:
    """异步执行测试用例生成工作流。"""
    logger.info(f"[Celery] 开始测试用例生成任务: {test_task_id}")
    try:
        status = run_async(_generate(test_task_id))
        return {"testTaskId": test_task_id, "status": status}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Celery] 测试用例生成失败 {test_task_id}: {exc}")
        raise self.retry(exc=exc, countdown=5)

"""文档生成相关 Celery 任务。参照 plans/phase1_backend.md §8。"""

from __future__ import annotations

import asyncio

from app.core.logging import logger
from app.tasks import celery_app


async def _generate(doc_task_id: str) -> None:
    from app.core.database import async_session
    from app.models import DocumentTask
    from app.services.document_service import DocumentService

    async with async_session() as db:
        task = await db.get(DocumentTask, doc_task_id)
        if task is None:
            logger.error(f"文档任务不存在: {doc_task_id}")
            return
        try:
            await DocumentService(db).run_generation(task)
            await db.commit()
        except Exception:  # noqa: BLE001
            await db.commit()  # 持久化 failed 状态
            raise


async def _submit(doc_id: str) -> None:
    from app.core.database import async_session
    from app.services.document_service import DocumentService

    async with async_session() as db:
        await DocumentService(db).submit_document(doc_id)
        await db.commit()


@celery_app.task(name="document.generate", bind=True, max_retries=2)
def generate_document_task(self, doc_task_id: str) -> dict:
    """异步执行文档生成工作流。"""
    logger.info(f"[Celery] 开始文档生成任务: {doc_task_id}")
    try:
        asyncio.run(_generate(doc_task_id))
        return {"docTaskId": doc_task_id, "status": "completed"}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Celery] 文档生成失败 {doc_task_id}: {exc}")
        raise self.retry(exc=exc, countdown=5)


@celery_app.task(name="document.submit")
def submit_document_task(doc_id: str) -> dict:
    """异步提交文档到虚拟文档系统。"""
    logger.info(f"[Celery] 提交文档: {doc_id}")
    asyncio.run(_submit(doc_id))
    return {"docId": doc_id, "status": "submitted"}

"""Celery 异步任务。

启动 worker: cd server && celery -A app.tasks worker --loglevel=info
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "drg_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

# 导入任务模块以完成注册
from app.tasks import document_tasks, testcase_tasks  # noqa: E402,F401

__all__ = ["celery_app"]

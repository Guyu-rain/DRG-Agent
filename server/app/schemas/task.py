"""任务中心相关 Pydantic Schema。参照 plans/03_api_interfaces.md §7。"""

from __future__ import annotations

from typing import Any

from app.schemas.common import CamelModel


class TaskStepDetail(CamelModel):
    step: str
    status: str
    duration_ms: int | None = None


class TaskSummary(CamelModel):
    task_id: str
    type: str
    status: str
    created_at: Any | None = None
    finished_at: Any | None = None


class TaskDetail(CamelModel):
    task_id: str
    type: str
    status: str
    started_at: Any | None = None
    finished_at: Any | None = None
    duration_ms: int | None = None
    steps: list[dict] = []
    error: dict | None = None

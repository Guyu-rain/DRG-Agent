"""Celery 同步任务中的异步协程执行器。"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_runner: asyncio.Runner | None = None


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """在工作进程内复用事件循环，避免异步连接跨已关闭循环复用。"""
    global _runner
    if _runner is None:
        _runner = asyncio.Runner()
    return _runner.run(coro)

"""Celery 异步协程执行器测试。"""

import asyncio

from app.tasks.async_runner import run_async


async def _running_loop_id() -> int:
    return id(asyncio.get_running_loop())


def test_run_async_reuses_event_loop():
    first_loop = run_async(_running_loop_id())
    second_loop = run_async(_running_loop_id())

    assert second_loop == first_loop

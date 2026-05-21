"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1 import cases, documents, grouping, logs, rules, system, tasks, testcases

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(cases.router)
api_router.include_router(rules.router)
api_router.include_router(grouping.router)
api_router.include_router(documents.router)
api_router.include_router(testcases.router)
api_router.include_router(tasks.router)
api_router.include_router(system.router)
api_router.include_router(logs.router)

__all__ = ["api_router"]

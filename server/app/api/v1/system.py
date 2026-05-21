"""系统配置 API。参照 plans/03_api_interfaces.md §8。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import ok
from app.schemas.system import SystemConfigUpdate
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["系统配置"])


@router.get("/config", summary="获取系统配置")
async def get_config(db: AsyncSession = Depends(get_db)) -> dict:
    service = SystemService(db)
    return ok(await service.get_config())


@router.put("/config", summary="更新系统配置")
async def update_config(payload: SystemConfigUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    service = SystemService(db)
    config = await service.update_config(payload.model_dump(by_alias=True, exclude_none=True))
    return ok(config, message="系统配置已更新")


@router.post("/demo/init", summary="初始化演示数据")
async def init_demo(db: AsyncSession = Depends(get_db)) -> dict:
    service = SystemService(db)
    result = await service.init_demo_data()
    return ok(result, message=result["message"])


@router.get("/health", summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    service = SystemService(db)
    return ok(await service.health_check())

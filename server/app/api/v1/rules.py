"""规则管理 API。参照 plans/03_api_interfaces.md §3。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import ok
from app.services.rule_service import RuleService

router = APIRouter(prefix="/rules", tags=["规则管理"])


@router.post("/import", status_code=201, summary="导入规则文件")
async def import_rules(
    file: UploadFile = File(...),
    version_name: str = Form(..., alias="versionName"),
    description: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RuleService(db)
    content = await file.read()
    version = await service.import_rules(content, file.filename or "rules.json", version_name, description)
    return ok(
        {
            "versionId": version.id,
            "versionName": version.version_name,
            "status": version.status,
            "ruleCount": version.rule_counts,
            "parseErrors": version.parse_errors or [],
        },
        message="规则文件已上传并解析",
        code=201,
    )


@router.get("/versions", summary="获取规则版本列表")
async def list_versions(db: AsyncSession = Depends(get_db)) -> dict:
    service = RuleService(db)
    versions = await service.get_versions()
    return ok({"items": [service.to_summary(v) for v in versions], "total": len(versions)})


@router.get("/search", summary="按编码查询规则")
async def search_rules(
    code: str = Query(...),
    rule_type: str | None = Query(default=None, alias="ruleType"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RuleService(db)
    matches = await service.search_rules(code, rule_type)
    return ok({"matches": matches})


@router.get("/versions/{version_id}", summary="获取规则版本详情")
async def get_version(version_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = RuleService(db)
    version = await service.get_version(version_id)
    return ok(service.to_detail(version))


@router.post("/versions/{version_id}/activate", summary="激活规则版本")
async def activate_version(version_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = RuleService(db)
    version = await service.activate_version(version_id)
    return ok(service.to_summary(version), message="规则版本已激活")


@router.delete("/versions/{version_id}", summary="删除规则版本")
async def delete_version(version_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = RuleService(db)
    await service.delete_version(version_id)
    return ok({"versionId": version_id}, message="规则版本已删除")

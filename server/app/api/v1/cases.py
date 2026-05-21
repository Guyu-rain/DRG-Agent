"""病历管理 API。参照 plans/03_api_interfaces.md §2。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.schemas.case import CaseCreate, CaseUpdate
from app.schemas.common import ok, paginate
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["病历管理"])


@router.post("", status_code=201, summary="创建病历")
async def create_case(payload: CaseCreate, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    case = await service.create_case(payload.model_dump())
    return ok(
        {"caseId": case.id, "status": case.status, "createdAt": case.created_at},
        message="病历创建成功",
        code=201,
    )


@router.post("/{case_id}/parse", summary="解析病历")
async def parse_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    parsed = await service.parse_case(case_id)
    case = await service.get_case(case_id)
    return ok(
        {
            "caseId": case_id,
            "parsedData": parsed,
            "warnings": case.parse_warnings or [],
            "parseStatus": "completed" if case.status == "parsed" else case.status,
        },
        message="解析完成",
    )


@router.post("/{case_id}/validate", summary="校验病历编码")
async def validate_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    result = await service.validate_case(case_id)
    return ok(
        {
            "caseId": case_id,
            "isValid": result["is_valid"],
            "validationResults": result["results"],
            "errors": result["errors"],
            "warnings": result["warnings"],
        },
        message="校验完成",
    )


@router.get("", summary="获取病历列表")
async def list_cases(
    page_params: dict = Depends(pagination_params),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CaseService(db)
    cases, total = await service.get_cases(status=status, keyword=keyword, **page_params)
    items = []
    for case in cases:
        count = await service.count_groupings(case.id)
        items.append(service.to_summary(case, count))
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))


@router.get("/{case_id}", summary="获取病历详情")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    case = await service.get_case(case_id)
    return ok(service.to_detail(case))


@router.put("/{case_id}", summary="更新病历")
async def update_case(case_id: str, payload: CaseUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    case = await service.update_case(case_id, payload.model_dump(exclude_none=True))
    return ok(service.to_detail(case), message="病历更新成功")


@router.delete("/{case_id}", summary="删除病历")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = CaseService(db)
    await service.delete_case(case_id)
    return ok({"caseId": case_id}, message="病历已删除")

"""测试用例 API。参照 plans/03_api_interfaces.md §6。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.core.config import settings
from app.core.exceptions import ErrorCode, NotFoundException
from app.schemas.common import ok, paginate
from app.schemas.testcase import TestExportRequest, TestGenRequest, TestSubmitRequest
from app.services.testcase_service import TestCaseService

router = APIRouter(prefix="/testcases", tags=["测试用例"])


@router.post("/generate", status_code=202, summary="生成测试用例")
async def generate_testcases(payload: TestGenRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    task = await service.create_generation_task(payload.model_dump())
    await db.commit()
    if settings.TASKS_EAGER:
        await service.run_generation(task)
        await db.commit()
    else:
        from app.tasks.testcase_tasks import generate_testcases_task

        generate_testcases_task.apply_async(args=[task.id], task_id=task.id)
    return ok(
        {"testTaskId": task.id, "status": task.status, "createdAt": task.created_at,
         "generatedCount": task.generated_count},
        message="测试用例生成任务已创建",
        code=202,
    )


@router.post("/export", summary="导出测试用例")
async def export_testcases(payload: TestExportRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    url = await service.export_testcases(payload.test_case_ids, payload.format)
    return ok({"downloadUrl": url}, message="测试用例已导出")


@router.post("/submit-to-documents", summary="提交测试用例到文档系统")
async def submit_to_documents(payload: TestSubmitRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    task = await service.create_document_task(
        payload.test_case_ids, payload.doc_title, payload.doc_type
    )
    await db.commit()
    if settings.TASKS_EAGER:
        from app.services.document_service import DocumentService

        await DocumentService(db).run_generation(task)
        await db.commit()
    else:
        from app.tasks.document_tasks import generate_document_task

        generate_document_task.apply_async(args=[task.id], task_id=task.id)
    return ok({"docTaskId": task.id}, message="测试用例已提交到文档系统")


@router.get("/tasks/{test_task_id}", summary="查询测试用例生成状态")
async def get_test_task(test_task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    task = await service.get_task(test_task_id)
    return ok({
        "testTaskId": task.id,
        "status": task.status,
        "generatedCount": task.generated_count,
        "errorMessage": task.error_message,
    })


@router.get("/export/{filename}", summary="下载导出文件")
async def download_export(filename: str) -> FileResponse:
    file_path = settings.document_storage_dir / "exports" / filename
    if not file_path.exists():
        raise NotFoundException(ErrorCode.DOCUMENT_NOT_FOUND, f"导出文件不存在: {filename}")
    return FileResponse(file_path, filename=filename)


@router.get("", summary="获取测试用例列表")
async def list_testcases(
    page_params: dict = Depends(pagination_params),
    scenario_type: str | None = Query(default=None, alias="scenarioType"),
    rule_version_id: str | None = Query(default=None, alias="ruleVersionId"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TestCaseService(db)
    cases, total = await service.get_testcases(
        scenario_type=scenario_type, rule_version_id=rule_version_id, **page_params
    )
    items = [service.to_summary(c) for c in cases]
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))


@router.get("/{test_case_id}", summary="获取单个测试用例")
async def get_testcase(test_case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    tc = await service.get_testcase(test_case_id)
    return ok(service.to_detail(tc))


@router.post("/{test_case_id}/execute", summary="执行单个测试用例")
async def execute_testcase(test_case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = TestCaseService(db)
    tc = await service.execute_testcase(test_case_id)
    return ok({
        "testCaseId": tc.id,
        "actualResult": tc.actual_result,
        "expectedResult": tc.expected_result,
        "isPassed": tc.is_passed,
        "executedAt": tc.executed_at,
    }, message="测试用例执行完成")

"""文档系统 API。参照 plans/03_api_interfaces.md §5。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.schemas.common import ok, paginate
from app.schemas.document import DocumentEditRequest, DocumentGenerateRequest, DocumentStatusUpdate
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["文档系统"])


@router.post("/generate", status_code=202, summary="生成文档")
async def generate_document(payload: DocumentGenerateRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    task = await service.generate_document(payload.model_dump())
    return ok(
        {"docTaskId": task.id, "status": task.status, "createdAt": task.created_at,
         "resultDocId": task.result_doc_id},
        message="文档生成任务已完成",
        code=202,
    )


@router.get("/tasks/{doc_task_id}", summary="查询文档生成状态")
async def get_document_task(doc_task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    task = await service.get_task(doc_task_id)
    return ok({
        "docTaskId": task.id,
        "status": task.status,
        "docId": task.result_doc_id,
        "errorMessage": task.error_message,
    })


@router.get("/{doc_id}/preview", summary="获取文档预览")
async def preview_document(doc_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    return ok(service.to_detail(doc))


@router.get("/{doc_id}/versions", summary="获取文档版本历史")
async def get_document_versions(doc_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    versions = await service.get_versions(doc_id)
    return ok({
        "items": [
            {"version": v.version, "changeDescription": v.change_description, "createdAt": v.created_at}
            for v in versions
        ],
        "total": len(versions),
    })


@router.get("/{doc_id}/download", summary="下载文档", response_class=PlainTextResponse)
async def download_document(
    doc_id: str, format: str = Query(default="markdown"), db: AsyncSession = Depends(get_db)
) -> PlainTextResponse:
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    filename = f"{doc.id}.md"
    return PlainTextResponse(
        content=doc.content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{doc_id}", summary="获取文档详情")
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    return ok(service.to_detail(doc))


@router.put("/{doc_id}", summary="编辑文档")
async def edit_document(
    doc_id: str, payload: DocumentEditRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    doc = await service.edit_document(doc_id, payload.content, payload.title)
    return ok(service.to_detail(doc), message="文档已更新")


@router.patch("/{doc_id}/status", summary="更新文档状态")
async def update_document_status(
    doc_id: str, payload: DocumentStatusUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    doc = await service.update_status(doc_id, payload.status)
    return ok({"docId": doc.id, "status": doc.status}, message="文档状态已更新")


@router.post("/{doc_id}/submit", summary="提交文档到虚拟文档系统")
async def submit_document(doc_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    record = await service.submit_document(doc_id)
    return ok(record, message="文档已提交")


@router.delete("/{doc_id}", summary="删除文档")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    await service.delete_document(doc_id)
    return ok({"docId": doc_id}, message="文档已删除")


@router.get("", summary="获取文档列表")
async def list_documents(
    page_params: dict = Depends(pagination_params),
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = DocumentService(db)
    docs, total = await service.get_documents(
        doc_type=type, status=status, keyword=keyword, **page_params
    )
    items = [service.to_summary(d) for d in docs]
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))

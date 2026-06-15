"""文档系统 API。参照 plans/03_api_interfaces.md §5。"""

from __future__ import annotations

import html

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, pagination_params
from app.core.config import settings
from app.core.exceptions import BadRequestException, ErrorCode
from app.schemas.common import ok, paginate
from app.schemas.document import (
    ConversationCreateRequest,
    DocumentEditRequest,
    DocumentGenerateRequest,
    DocumentStatusUpdate,
    MessageSendRequest,
    QaSendRequest,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["文档系统"])


# ----------------------------------------------------- 对话式文档生成
# 注意: 以下 /conversations 路由必须定义在 /{doc_id} 之前, 否则会被其捕获。
@router.post("/conversations", status_code=201, summary="创建文档对话会话")
async def create_conversation(
    payload: ConversationCreateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    conv = await service.create_conversation(payload.title, payload.doc_type)
    await db.commit()
    return ok(service.to_conversation_summary(conv), message="会话已创建", code=201)


@router.get("/conversations", summary="获取文档对话会话列表")
async def list_conversations(
    page_params: dict = Depends(pagination_params), db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    convs, total = await service.get_conversations(**page_params)
    items = [service.to_conversation_summary(c) for c in convs]
    return ok(paginate(items, total, page_params["page"], page_params["page_size"]))


@router.get("/conversations/{conv_id}", summary="获取会话详情与消息")
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    conv = await service.get_conversation(conv_id)
    messages = await service.get_messages(conv_id)
    document = None
    if conv.document_id:
        doc = await service.get_document(conv.document_id)
        document = service.to_detail(doc)
    return ok({
        **service.to_conversation_summary(conv),
        "messages": [service.to_message(m) for m in messages],
        "document": document,
    })


@router.post("/conversations/{conv_id}/messages", summary="发送指令并生成/修订文档")
async def send_message(
    conv_id: str, payload: MessageSendRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    result = await service.send_message(conv_id, payload.instruction)
    await db.commit()
    return ok(result, message="文档已更新")


# ----------------------------------------------------- Q&A 模式
@router.post("/qa/conversations", status_code=201, summary="创建 Q&A 对话会话")
async def create_qa_conversation(
    payload: ConversationCreateRequest | None = None, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    title = payload.title if payload else None
    conv = await service.create_conversation(title=title, mode="qa")
    await db.commit()
    return ok(service.to_conversation_summary(conv), message="Q&A 会话已创建", code=201)


@router.get("/qa/conversations", summary="获取 Q&A 对话会话列表")
async def list_qa_conversations(
    page_params: dict = Depends(pagination_params), db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    convs, total = await service.get_conversations(**page_params)
    qa_convs = [c for c in convs if c.mode == "qa"]
    items = [service.to_conversation_summary(c) for c in qa_convs]
    return ok(paginate(items, len(items), 1, 50))


@router.get("/qa/conversations/{conv_id}", summary="获取 Q&A 会话详情与消息")
async def get_qa_conversation(conv_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    conv = await service.get_conversation(conv_id)
    messages = await service.get_messages(conv_id)
    return ok({
        **service.to_conversation_summary(conv),
        "messages": [service.to_message(m) for m in messages],
    })


@router.post("/qa/conversations/{conv_id}/messages", summary="发送 Q&A 问题")
async def send_qa_message(
    conv_id: str, payload: QaSendRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DocumentService(db)
    result = await service.send_qa_message(conv_id, payload.instruction)
    await db.commit()
    return ok(result, message="回答已生成")


@router.delete("/conversations/{conv_id}", summary="删除会话")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    await service.delete_conversation(conv_id)
    await db.commit()
    return ok({"conversationId": conv_id}, message="会话已删除")


@router.post("/generate", status_code=202, summary="生成文档")
async def generate_document(payload: DocumentGenerateRequest, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    task = await service.create_generation_task(payload.model_dump())
    await db.commit()
    if settings.TASKS_EAGER:
        await service.run_generation(task)
        await db.commit()
    else:
        from app.tasks.document_tasks import generate_document_task

        generate_document_task.apply_async(args=[task.id], task_id=task.id)
    return ok(
        {"docTaskId": task.id, "status": task.status, "createdAt": task.created_at,
         "resultDocId": task.result_doc_id},
        message="文档生成任务已创建",
        code=202,
    )


@router.get("/tasks/{doc_task_id}", summary="查询文档生成状态")
async def get_document_task(doc_task_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    service = DocumentService(db)
    task = await service.get_task(doc_task_id)
    return ok({
        "docTaskId": task.id,
        "status": task.status,
        "createdAt": task.created_at,
        "resultDocId": task.result_doc_id,
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


@router.get("/{doc_id}/download", summary="下载文档")
async def download_document(
    doc_id: str, format: str = Query(default="markdown"), db: AsyncSession = Depends(get_db)
) -> Response:
    service = DocumentService(db)
    doc = await service.get_document(doc_id)
    fmt = format.lower()
    if fmt in ("markdown", "md"):
        content = doc.content.encode("utf-8")
        suffix, media_type = "md", "text/markdown; charset=utf-8"
    elif fmt == "html":
        body = "<br>\n".join(html.escape(line) for line in doc.content.splitlines())
        content = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(doc.title)}</title></head><body>{body}</body></html>"
        ).encode("utf-8")
        suffix, media_type = "html", "text/html; charset=utf-8"
    elif fmt == "pdf":
        content = _make_pdf(doc.title, doc.content)
        suffix, media_type = "pdf", "application/pdf"
    else:
        raise BadRequestException(
            ErrorCode.REQUIRED_FIELD_MISSING,
            f"不支持的文档格式: {format}，可选 markdown/html/pdf",
        )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.id}.{suffix}"'},
    )


def _make_pdf(title: str, content: str) -> bytes:
    """生成使用 PDF 内置 CJK 字体的轻量文本 PDF。"""
    lines = [title, ""] + content.splitlines()
    pages = [lines[i:i + 42] for i in range(0, len(lines), 42)] or [[]]
    objects: list[bytes] = []

    def add(value: bytes) -> int:
        objects.append(value)
        return len(objects)

    catalog_id = add(b"")
    pages_id = add(b"")
    font_id = add(
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>"
    )
    page_ids: list[int] = []
    content_ids: list[int] = []
    descendant_id = add(
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> >>"
    )
    assert descendant_id == 4

    for page_lines in pages:
        commands = ["BT", "/F1 11 Tf", "50 790 Td", "15 TL"]
        for line in page_lines:
            encoded = line[:100].encode("utf-16-be").hex().upper()
            commands.append(f"<{encoded}> Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        content_ids.append(add(
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        ))
        page_ids.append(add(b""))

    for page_id, content_id in zip(page_ids, content_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Count {len(page_ids)} /Kids "
        f"[{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] >>"
    ).encode()
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


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

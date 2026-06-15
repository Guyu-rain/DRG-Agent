"""文档服务层测试。"""

import asyncio
import time

import pytest
from app.core.exceptions import AppException, ErrorCode
from app.models import Document, DocumentConversation, DocumentMessage, DocumentVersion
from app.services.document_service import DocumentService
from app.services.task_service import TaskService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def test_generate_document(db_session):
    service = DocumentService(db_session)
    task = await service.generate_document({
        "doc_type": "requirements",
        "title": "测试需求文档",
        "context": {},
    })
    assert task.status == "completed"
    assert task.result_doc_id is not None

    doc = await service.get_document(task.result_doc_id)
    assert doc.content
    assert doc.status == "draft"


async def test_edit_document_creates_version(db_session):
    service = DocumentService(db_session)
    task = await service.generate_document({"doc_type": "design", "title": "设计文档", "context": {}})
    doc = await service.edit_document(task.result_doc_id, "# 修改后的内容", "新标题")
    assert doc.title == "新标题"
    assert doc.version == "V1.1"
    versions = await service.get_versions(doc.id)
    assert len(versions) == 1


async def test_submit_document(db_session):
    service = DocumentService(db_session)
    task = await service.generate_document({"doc_type": "testing", "title": "测试文档", "context": {}})
    record = await service.submit_document(task.result_doc_id)
    assert record["status"] == "submitted"
    assert record["submissionRecord"]["checksum"].startswith("sha256:")


async def test_cancel_running_generation_discards_result(db_session, db_engine, monkeypatch):
    class SlowOrchestrator:
        def execute_document_gen(self, *_args, **_kwargs):
            time.sleep(0.15)
            return {"formatted_content": "# should be discarded"}

    monkeypatch.setattr("app.agents.get_orchestrator", lambda: SlowOrchestrator())
    service = DocumentService(db_session)
    task = await service.create_generation_task({
        "doc_type": "requirements",
        "title": "取消中的文档",
        "context": {},
    })
    await db_session.commit()

    generation = asyncio.create_task(service.run_generation(task))
    await asyncio.sleep(0.05)

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as cancel_session:
        result = await TaskService(cancel_session).cancel_task(task.id)
        assert result["status"] == "cancelled"

    assert await generation is None
    await db_session.refresh(task)
    assert task.status == "cancelled"
    assert task.result_doc_id is None
    assert (await db_session.execute(select(func.count()).select_from(Document))).scalar_one() == 0


async def test_invalid_chat_output_preserves_document_and_history(db_session, monkeypatch):
    class InvalidOrchestrator:
        def execute_document_chat(self, *_args, **_kwargs):
            return (
                "<｜｜DSML｜｜tool_calls>"
                '<｜｜DSML｜｜invoke name="read_source_file"></｜｜DSML｜｜invoke>'
                "</｜｜DSML｜｜tool_calls>"
            )

    doc = Document(
        doc_type="testing",
        title="稳定版本",
        content="# 稳定版本\n\n原始内容",
        original_content="# 稳定版本\n\n原始内容",
    )
    db_session.add(doc)
    await db_session.flush()
    conv = DocumentConversation(title="测试会话", doc_type="testing", document_id=doc.id)
    db_session.add(conv)
    await db_session.flush()
    monkeypatch.setattr("app.agents.get_orchestrator", lambda: InvalidOrchestrator())

    with pytest.raises(AppException) as exc_info:
        await DocumentService(db_session).send_message(conv.id, "继续扩写")

    assert exc_info.value.code == ErrorCode.DOCUMENT_GEN_FAILED
    assert exc_info.value.http_status == 502
    await db_session.refresh(doc)
    assert doc.content == "# 稳定版本\n\n原始内容"
    assert doc.version == "V1.0"
    assert (
        await db_session.execute(select(func.count()).select_from(DocumentVersion))
    ).scalar_one() == 0
    assert (
        await db_session.execute(select(func.count()).select_from(DocumentMessage))
    ).scalar_one() == 0

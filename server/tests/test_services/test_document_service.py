"""文档服务层测试。"""

from app.services.document_service import DocumentService


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

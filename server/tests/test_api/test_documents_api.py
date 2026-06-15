"""文档系统 API 测试。"""


async def _generate_doc(client) -> str:
    resp = await client.post("/api/v1/documents/generate", json={
        "docType": "requirements", "title": "API 测试文档", "context": {},
    })
    assert resp.status_code == 202
    return resp.json()["data"]["resultDocId"]


async def test_generate_and_get_document(client):
    doc_id = await _generate_doc(client)
    resp = await client.get(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["content"]


async def test_submit_document(client):
    doc_id = await _generate_doc(client)
    resp = await client.post(f"/api/v1/documents/{doc_id}/submit")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "submitted"


async def test_list_documents(client):
    await _generate_doc(client)
    resp = await client.get("/api/v1/documents?page=1&pageSize=20")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


async def test_document_not_found(client):
    resp = await client.get("/api/v1/documents/DOC-NOPE")
    assert resp.status_code == 404


async def test_download_document_formats(client):
    doc_id = await _generate_doc(client)
    expectations = {
        "markdown": ("text/markdown", f"{doc_id}.md"),
        "html": ("text/html", f"{doc_id}.html"),
        "pdf": ("application/pdf", f"{doc_id}.pdf"),
    }

    for fmt, (content_type, filename) in expectations.items():
        resp = await client.get(f"/api/v1/documents/{doc_id}/download?format={fmt}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(content_type)
        assert filename in resp.headers["content-disposition"]
        assert resp.content

    pdf = await client.get(f"/api/v1/documents/{doc_id}/download?format=pdf")
    assert pdf.content.startswith(b"%PDF-1.4")


async def test_download_document_rejects_unknown_format(client):
    doc_id = await _generate_doc(client)
    resp = await client.get(f"/api/v1/documents/{doc_id}/download?format=docx")
    assert resp.status_code == 400


# ----------------------------------------------------- 对话式文档生成


async def test_conversation_create_and_chat(client):
    # 创建会话
    create = await client.post(
        "/api/v1/documents/conversations",
        json={"title": "需求文档对话", "docType": "requirements"},
    )
    assert create.status_code == 201
    conv_id = create.json()["data"]["conversationId"]

    # 第一轮: 新建文档
    first = await client.post(
        f"/api/v1/documents/conversations/{conv_id}/messages",
        json={"instruction": "帮我起草一份需求分析文档"},
    )
    assert first.status_code == 200
    data = first.json()["data"]
    assert data["assistantMessage"]["role"] == "assistant"
    doc_id = data["document"]["docId"]
    assert data["document"]["content"]
    assert data["document"]["version"] == "V1.0"

    # 第二轮: 修订, 文档版本应递增且仍指向同一篇
    second = await client.post(
        f"/api/v1/documents/conversations/{conv_id}/messages",
        json={"instruction": "增加非功能需求章节"},
    )
    assert second.status_code == 200
    second_doc = second.json()["data"]["document"]
    assert second_doc["docId"] == doc_id
    assert second_doc["version"] == "V1.1"

    # 会话详情应包含 4 条消息 (2 user + 2 assistant) 与当前文档
    detail = await client.get(f"/api/v1/documents/conversations/{conv_id}")
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert len(detail_data["messages"]) == 4
    assert detail_data["document"]["docId"] == doc_id


async def test_conversation_list_and_delete(client):
    create = await client.post("/api/v1/documents/conversations", json={})
    conv_id = create.json()["data"]["conversationId"]

    listing = await client.get("/api/v1/documents/conversations?page=1&pageSize=20")
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] >= 1

    deleted = await client.delete(f"/api/v1/documents/conversations/{conv_id}")
    assert deleted.status_code == 200
    missing = await client.get(f"/api/v1/documents/conversations/{conv_id}")
    assert missing.status_code == 404

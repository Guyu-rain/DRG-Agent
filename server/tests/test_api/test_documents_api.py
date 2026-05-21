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

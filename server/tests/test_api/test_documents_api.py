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

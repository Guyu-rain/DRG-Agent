"""病历管理 API 测试。"""


async def test_create_case_structured(client):
    resp = await client.post("/api/v1/cases", json={
        "sourceType": "structured",
        "structuredData": {"主要诊断": {"疾病名称": "脑膜炎", "疾病编码": "A01.002+G01*"}},
    })
    assert resp.status_code == 201
    assert resp.json()["data"]["caseId"].startswith("CASE-")


async def test_get_case_detail(client):
    created = await client.post("/api/v1/cases", json={
        "sourceType": "structured",
        "structuredData": {"主要诊断": {"疾病名称": "脑膜炎", "疾病编码": "A01.002+G01*"}},
    })
    case_id = created.json()["data"]["caseId"]
    resp = await client.get(f"/api/v1/cases/{case_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["primaryDiagnosis"]["code"] == "A01.002+G01*"


async def test_get_case_not_found(client):
    resp = await client.get("/api/v1/cases/CASE-NOPE")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40401


async def test_list_cases(seeded_client):
    resp = await seeded_client.get("/api/v1/cases?page=1&pageSize=20")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 3


async def test_validate_case(client):
    created = await client.post("/api/v1/cases", json={
        "sourceType": "structured",
        "structuredData": {"主要诊断": {"疾病名称": "脑膜炎", "疾病编码": "A01.002+G01*"}},
    })
    case_id = created.json()["data"]["caseId"]
    resp = await client.post(f"/api/v1/cases/{case_id}/validate")
    assert resp.status_code == 200
    assert resp.json()["data"]["isValid"] is True


async def test_delete_case(client):
    created = await client.post("/api/v1/cases", json={
        "sourceType": "structured",
        "structuredData": {"主要诊断": {"疾病名称": "x", "疾病编码": "A01"}},
    })
    case_id = created.json()["data"]["caseId"]
    resp = await client.delete(f"/api/v1/cases/{case_id}")
    assert resp.status_code == 200
    assert (await client.get(f"/api/v1/cases/{case_id}")).status_code == 404

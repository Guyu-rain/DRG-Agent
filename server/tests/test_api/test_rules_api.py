"""规则管理 API 测试。"""


async def test_list_versions(seeded_client):
    resp = await seeded_client.get("/api/v1/rules/versions")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


async def test_get_version_detail(seeded_client):
    versions = (await seeded_client.get("/api/v1/rules/versions")).json()["data"]["items"]
    version_id = versions[0]["versionId"]
    resp = await seeded_client.get(f"/api/v1/rules/versions/{version_id}")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["mdcList"]) >= 1


async def test_get_version_not_found(client):
    resp = await client.get("/api/v1/rules/versions/RV-NOPE")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40402


async def test_search_rules(seeded_client):
    resp = await seeded_client.get("/api/v1/rules/search?code=A01.002&ruleType=mdc")
    assert resp.status_code == 200
    matches = resp.json()["data"]["matches"]
    assert any(m["code"] == "MDCB" for m in matches)

"""系统配置 API 测试。"""


async def test_health_check(client):
    resp = await client.get("/api/v1/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["status"] in ("healthy", "degraded")
    assert "database" in body["data"]["components"]


async def test_demo_init(client):
    resp = await client.post("/api/v1/system/demo/init")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ruleVersionId"]
    assert len(data["sampleCaseIds"]) >= 3


async def test_demo_init_idempotent(client):
    first = (await client.post("/api/v1/system/demo/init")).json()["data"]
    second = (await client.post("/api/v1/system/demo/init")).json()["data"]
    assert first["ruleVersionId"] == second["ruleVersionId"]


async def test_get_config(client):
    resp = await client.get("/api/v1/system/config")
    assert resp.status_code == 200
    assert resp.json()["data"]["llm"]["timeoutSeconds"] is None


async def test_update_config(client):
    resp = await client.put("/api/v1/system/config", json={"llm": {"model": "deepseek-chat"}})
    assert resp.status_code == 200

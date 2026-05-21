"""测试用例 API 测试。"""


async def test_generate_testcases(seeded_client):
    resp = await seeded_client.post("/api/v1/testcases/generate", json={
        "scenarioTypes": ["normal", "abnormal"], "maxCount": 20,
    })
    assert resp.status_code == 202
    assert resp.json()["data"]["status"] == "completed"


async def test_list_testcases(seeded_client):
    await seeded_client.post("/api/v1/testcases/generate", json={
        "scenarioTypes": ["normal"], "maxCount": 10,
    })
    resp = await seeded_client.get("/api/v1/testcases?page=1&pageSize=20")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


async def test_test_task_not_found(client):
    resp = await client.get("/api/v1/testcases/tasks/TEST-TASK-NOPE")
    assert resp.status_code == 404

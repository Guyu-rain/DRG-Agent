"""任务中心 API 测试。"""


async def test_list_tasks(seeded_client):
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    await seeded_client.post("/api/v1/grouping/execute", json={"caseId": items[0]["caseId"]})
    resp = await seeded_client.get("/api/v1/tasks?type=all")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


async def test_get_task_detail(seeded_client):
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    exec_resp = await seeded_client.post("/api/v1/grouping/execute", json={"caseId": items[0]["caseId"]})
    task_id = exec_resp.json()["data"]["taskId"]
    resp = await seeded_client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "grouping"
    assert len(resp.json()["data"]["steps"]) == 5


async def test_task_not_found(client):
    resp = await client.get("/api/v1/tasks/TASK-NOPE")
    assert resp.status_code == 404


async def test_logs_endpoint(seeded_client):
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    await seeded_client.post("/api/v1/grouping/execute", json={"caseId": items[0]["caseId"]})
    resp = await seeded_client.get("/api/v1/logs")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1

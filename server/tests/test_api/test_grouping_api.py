"""DRG 入组 API 测试。"""


async def _first_case_id(client) -> str:
    items = (await client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    # 课程示例病历 (A01.002) 优先
    for item in items:
        if "A01.002" in (item.get("summary") or ""):
            return item["caseId"]
    return items[0]["caseId"]


async def test_execute_grouping_course_example(seeded_client):
    case_id = await _first_case_id(seeded_client)
    resp = await seeded_client.post("/api/v1/grouping/execute", json={"caseId": case_id})
    assert resp.status_code == 202
    task_id = resp.json()["data"]["taskId"]

    result = await seeded_client.get(f"/api/v1/grouping/results/{task_id}")
    assert result.status_code == 200
    data = result.json()["data"]
    assert data["result"]["drg"]["code"] == "BB11"
    assert data["ruleVersionId"]
    assert data["ruleVersion"] == "DRG 2.0 演示规则"


async def test_grouping_result_not_found(client):
    resp = await client.get("/api/v1/grouping/results/TASK-NOPE")
    assert resp.status_code == 404


async def test_list_grouping_tasks(seeded_client):
    case_id = await _first_case_id(seeded_client)
    await seeded_client.post("/api/v1/grouping/execute", json={"caseId": case_id})
    resp = await seeded_client.get("/api/v1/grouping/tasks")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


async def test_batch_grouping(seeded_client):
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    ids = [it["caseId"] for it in items[:2]]
    resp = await seeded_client.post("/api/v1/grouping/batch", json={"caseIds": ids})
    assert resp.status_code == 202
    assert resp.json()["data"]["totalCases"] == 2

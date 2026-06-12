"""测试用例 API 测试。"""


async def test_generate_testcases(seeded_client):
    resp = await seeded_client.post("/api/v1/testcases/generate", json={
        "scenarioTypes": ["normal", "boundary", "abnormal"], "maxCount": 50,
    })
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert data["generatedCount"] == 31

    items = (
        await seeded_client.get("/api/v1/testcases?page=1&pageSize=50")
    ).json()["data"]["items"]
    scenario_types = [item["scenarioType"] for item in items]
    assert scenario_types.count("normal") == 12
    assert scenario_types.count("boundary") == 12
    assert scenario_types.count("abnormal") == 7
    assert all("isGrouped" in item["expectedResult"] for item in items)


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


async def test_execute_generated_testcase(seeded_client):
    await seeded_client.post("/api/v1/testcases/generate", json={
        "scenarioTypes": ["normal"], "maxCount": 1,
    })
    items = (
        await seeded_client.get("/api/v1/testcases?page=1&pageSize=10")
    ).json()["data"]["items"]

    resp = await seeded_client.post(f"/api/v1/testcases/{items[0]['testCaseId']}/execute")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["isPassed"] is True
    assert data["actualResult"] == data["expectedResult"]
    assert data["executedAt"]

    listed = (
        await seeded_client.get("/api/v1/testcases?page=1&pageSize=10")
    ).json()["data"]["items"][0]
    assert listed["isPassed"] is True
    assert listed["actualResult"] == listed["expectedResult"]

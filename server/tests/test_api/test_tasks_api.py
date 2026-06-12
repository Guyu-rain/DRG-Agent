"""任务中心 API 测试。"""

from app.models import TestTask as PendingTaskModel


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


async def test_submit_review_completed_task(seeded_client):
    """将已完成的入组任务提交复核。"""
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    exec_resp = await seeded_client.post("/api/v1/grouping/execute", json={"caseId": items[0]["caseId"]})
    task_id = exec_resp.json()["data"]["taskId"]

    resp = await seeded_client.post(f"/api/v1/tasks/{task_id}/review")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "needs_review"


async def test_submit_review_not_found(client):
    """提交不存在的任务复核应返回 404。"""
    resp = await client.post("/api/v1/tasks/TASK-NOPE/review")
    assert resp.status_code == 404


async def test_submit_review_non_grouping_task_fails(seeded_client):
    """非分组任务提交复核应返回 404。"""
    resp = await seeded_client.post("/api/v1/tasks/DOC-TASK-NOPE/review")
    assert resp.status_code == 404


async def test_cancel_pending_test_task(client, db_engine):
    """待执行任务可取消，并持久化 cancelled 状态。"""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        task = PendingTaskModel(status="pending", scenario_types=["normal"], max_count=1)
        session.add(task)
        await session.commit()
        task_id = task.id

    resp = await client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"

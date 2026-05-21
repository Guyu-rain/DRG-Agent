"""演示场景端到端集成测试 (HTTP -> 服务 -> 引擎 -> 数据库)。"""


# 4 个示例回归用例
_EXPECTED = {
    "A01.002+G01*": ("MDCB", "BB1", "BB11"),
    "C16.301": ("MDCG", "GB2", "GB29"),
    "J86.000x013": ("MDCE", "EC2", "EC29"),
    "K83.105": ("MDCH", "HC1", "HC15"),
}


async def test_demo_init_then_group_all_cases(seeded_client):
    """初始化演示数据后, 对全部样例病历执行入组并校验结果。"""
    items = (await seeded_client.get("/api/v1/cases?pageSize=20")).json()["data"]["items"]
    assert len(items) >= 4

    checked = 0
    for item in items:
        case_id = item["caseId"]
        detail = (await seeded_client.get(f"/api/v1/cases/{case_id}")).json()["data"]
        primary = (detail["primaryDiagnosis"] or {}).get("code")
        if primary not in _EXPECTED:
            continue
        exec_resp = await seeded_client.post("/api/v1/grouping/execute", json={"caseId": case_id})
        task_id = exec_resp.json()["data"]["taskId"]
        result = (await seeded_client.get(f"/api/v1/grouping/results/{task_id}")).json()["data"]
        mdc, adrg, drg = _EXPECTED[primary]
        assert result["result"]["mdc"]["code"] == mdc
        assert result["result"]["adrg"]["code"] == adrg
        assert result["result"]["drg"]["code"] == drg
        checked += 1
    assert checked == 4


async def test_document_full_lifecycle(client):
    """文档生成 -> 编辑 -> 提交 全流程。"""
    gen = await client.post("/api/v1/documents/generate", json={
        "docType": "requirements", "title": "集成测试文档", "context": {},
    })
    doc_id = gen.json()["data"]["resultDocId"]

    edit = await client.put(f"/api/v1/documents/{doc_id}", json={"content": "# 编辑后内容"})
    assert edit.json()["data"]["version"] == "V1.1"

    submit = await client.post(f"/api/v1/documents/{doc_id}/submit")
    assert submit.json()["data"]["status"] == "submitted"


async def test_testcase_generation_and_export(seeded_client):
    """测试用例生成 -> 导出 全流程。"""
    await seeded_client.post("/api/v1/testcases/generate", json={
        "scenarioTypes": ["normal", "boundary", "abnormal"], "maxCount": 30,
    })
    items = (await seeded_client.get("/api/v1/testcases?pageSize=50")).json()["data"]["items"]
    assert len(items) > 0
    ids = [it["testCaseId"] for it in items[:3]]
    export = await seeded_client.post("/api/v1/testcases/export", json={"testCaseIds": ids})
    assert export.json()["data"]["downloadUrl"].endswith(".xlsx")


async def test_nocode_case_does_not_block(client):
    """无编码病历: 校验产生 warning 但不报 error。"""
    created = await client.post("/api/v1/cases", json={
        "sourceType": "structured",
        "structuredData": {"主要诊断": "胃窦恶性肿瘤"},  # 仅名称无编码
    })
    case_id = created.json()["data"]["caseId"]
    validate = await client.post(f"/api/v1/cases/{case_id}/validate")
    data = validate.json()["data"]
    assert data["isValid"] is True
    assert len(data["warnings"]) >= 1

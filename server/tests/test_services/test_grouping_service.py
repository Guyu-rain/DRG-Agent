"""入组服务层测试。"""

from app.services.case_service import CaseService
from app.services.grouping_service import GroupingService


async def _make_case(db_session, structured: dict):
    return await CaseService(db_session).create_case(
        {"source_type": "structured", "structured_data": structured}
    )


async def test_execute_grouping_course_example(db_session, rule_version):
    case = await _make_case(db_session, {
        "主要诊断": {"疾病名称": "伤寒性脑膜炎", "疾病编码": "A01.002+G01*"},
        "次要诊断列表": [{"疾病名称": "急性呼吸衰竭", "疾病编码": "J96.0"}],
        "主要手术": {"手术名称": "动脉内膜剥脱术", "手术编码": "38.1000x002"},
    })
    service = GroupingService(db_session)
    task = await service.execute_grouping(case.id, rule_version.id)
    assert task.status == "completed"

    result = await service.get_grouping_result(task.id)
    assert result["result"]["drg"]["code"] == "BB11"
    assert len(result["result"]["evidence"]) == 5


async def test_execute_grouping_persists_steps(db_session, rule_version):
    case = await _make_case(db_session, {
        "主要诊断": {"疾病名称": "胆管狭窄", "疾病编码": "K83.105"},
        "主要手术": {"手术名称": "胆总管切除术", "手术编码": "51.6303"},
    })
    service = GroupingService(db_session)
    task = await service.execute_grouping(case.id, rule_version.id)
    from app.services.task_service import TaskService

    detail = await TaskService(db_session).get_task_detail(task.id)
    assert len(detail["steps"]) == 5


async def test_execute_grouping_unmatched_mdc(db_session, rule_version):
    case = await _make_case(db_session, {
        "主要诊断": {"疾病名称": "未知诊断", "疾病编码": "Z99.9"},
    })
    service = GroupingService(db_session)
    task = await service.execute_grouping(case.id, rule_version.id)
    assert task.status == "failed"
    result = await service.get_grouping_result(task.id)
    assert result["result"] is None
    assert result["error"] is not None

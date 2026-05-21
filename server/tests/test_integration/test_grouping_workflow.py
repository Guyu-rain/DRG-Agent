"""入组工作流端到端集成测试。"""

from app.agents import AgentOrchestrator
from app.llm import MockLLMClient


def _orch() -> AgentOrchestrator:
    return AgentOrchestrator(llm_client=MockLLMClient(default_response="（解释）"))


def test_workflow_course_example(rule_index, course_case):
    state = _orch().execute_grouping(
        "CASE-T", "RV-T", rule_index, structured_data=course_case
    )
    result = state["grouping_result"]
    assert result["is_grouped"] is True
    assert result["drg_code"] == "BB11"
    assert state["explanation"]
    assert state["status"] == "completed"


def test_workflow_invalid_code_routes_to_error(rule_index):
    bad_case = {"primaryDiagnosis": {"code": "BAD_CODE", "name": "x"}}
    state = _orch().execute_grouping("CASE-T", "RV-T", rule_index, structured_data=bad_case)
    assert state["status"] == "failed"
    assert state["grouping_result"]["is_grouped"] is False


def test_workflow_ungrouped_generates_failure_explanation(rule_index):
    case = {"primaryDiagnosis": {"code": "Z99.9", "name": "未知"}}
    state = _orch().execute_grouping("CASE-T", "RV-T", rule_index, structured_data=case)
    assert state["grouping_result"]["is_grouped"] is False
    assert state["explanation"]


def test_test_gen_workflow(rule_index, parsed_rules):
    state = _orch().execute_test_gen(
        "RV-T", ["normal", "abnormal"], {}, [], 20, rule_index, parsed_rules
    )
    assert state["status"] == "completed"
    assert len(state["test_cases"]) > 0

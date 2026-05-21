"""测试用例生成智能体 (LLM + 规则)。参照 plans/06_agent_workflow.md §4。"""

from __future__ import annotations

import json

from app.agents.state import TestGenState
from app.core.logging import logger
from app.engine.grouping_engine import GroupingEngine
from app.llm import parse_llm_json_output, render_prompt


def rule_analyze_agent(state: TestGenState) -> dict:
    """分析规则, 提取可测的条件组合。"""
    rules = state.get("parsed_rules") or {}
    analysis = {
        "mdc_count": len(rules.get("mdc_list", [])),
        "adrg_list": [
            {
                "code": a.get("code"),
                "mdc": a.get("mdc"),
                "is_surgical": a.get("is_surgical", bool(a.get("surgery_list"))),
                "surgery_list": a.get("surgery_list", []),
            }
            for a in rules.get("adrg_list", [])
        ],
        "mcc_codes": [m.get("code") for m in rules.get("mcc_list", [])],
        "cc_codes": [c.get("code") for c in rules.get("cc_list", [])],
    }
    return {"rule_analysis": analysis}


def scenario_construct_agent(state: TestGenState) -> dict:
    """确定性地构造正常/边界/异常测试场景。"""
    rules = state.get("parsed_rules") or {}
    analysis = state.get("rule_analysis") or {}
    scenario_types = state.get("scenario_types") or ["normal", "boundary", "abnormal"]
    max_count = state.get("max_count", 50)

    mdc_prefix = {m["code"]: (m.get("icd_prefixes") or [None])[0] for m in rules.get("mdc_list", [])}
    mcc_codes = analysis.get("mcc_codes", [])
    surgical = [a for a in analysis.get("adrg_list", []) if a["is_surgical"] and a["surgery_list"]]

    scenarios: list[dict] = []

    if "normal" in scenario_types:
        for adrg in surgical:
            diag = mdc_prefix.get(adrg["mdc"])
            if not diag:
                continue
            scenarios.append({
                "type": "normal",
                "description": f"正常场景: ADRG={adrg['code']} 手术命中",
                "input": {
                    "primaryDiagnosis": {"code": diag, "name": f"{adrg['mdc']} 示例诊断"},
                    "secondaryDiagnoses": [],
                    "primaryProcedure": {"code": adrg["surgery_list"][0], "name": "示例手术"},
                },
            })

    if "boundary" in scenario_types:
        for adrg in surgical:
            diag = mdc_prefix.get(adrg["mdc"])
            if not diag:
                continue
            if mcc_codes:
                scenarios.append({
                    "type": "boundary",
                    "description": f"边界场景: ADRG={adrg['code']} 伴 MCC",
                    "input": {
                        "primaryDiagnosis": {"code": diag, "name": "示例诊断"},
                        "secondaryDiagnoses": [{"code": mcc_codes[0], "name": "示例 MCC"}],
                        "primaryProcedure": {"code": adrg["surgery_list"][0], "name": "示例手术"},
                    },
                })
            scenarios.append({
                "type": "boundary",
                "description": f"边界场景: ADRG={adrg['code']} 无次要诊断",
                "input": {
                    "primaryDiagnosis": {"code": diag, "name": "示例诊断"},
                    "secondaryDiagnoses": [],
                    "primaryProcedure": {"code": adrg["surgery_list"][0], "name": "示例手术"},
                },
            })

    if "abnormal" in scenario_types:
        scenarios.extend([
            {"type": "abnormal", "description": "编码格式错误",
             "input": {"primaryDiagnosis": {"code": "ZZZ_999", "name": "非法编码"}}},
            {"type": "abnormal", "description": "主诊断缺失",
             "input": {"primaryDiagnosis": {"code": None, "name": None}}},
            {"type": "abnormal", "description": "编码无法匹配 MDC",
             "input": {"primaryDiagnosis": {"code": "Z99.9", "name": "无法匹配的诊断"}}},
        ])

    return {"scenarios": scenarios[:max_count]}


def testcase_generate_agent(state: TestGenState) -> dict:
    """根据场景生成测试用例。优先 LLM, 失败时用规则引擎确定性生成。"""
    scenarios = state.get("scenarios") or []
    analysis = state.get("rule_analysis") or {}
    llm = state.get("llm_client")

    deterministic = _deterministic_testcases(scenarios, state.get("rule_index") or {})

    if llm is not None:
        try:
            prompt = render_prompt(
                "testcase_generate",
                rule_analysis=json.dumps(analysis, ensure_ascii=False, indent=2),
                scenarios=json.dumps(scenarios, ensure_ascii=False, indent=2),
            )
            output = llm.call(prompt)
            parsed = parse_llm_json_output(output)
            if isinstance(parsed, list) and parsed:
                return {"test_cases": parsed, "status": "completed"}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"测试用例 LLM 生成失败, 改用规则引擎: {exc}")

    return {"test_cases": deterministic, "status": "completed"}


def save_testcases_agent(state: TestGenState) -> dict:
    """工作流结束标记。实际落库由 Celery 任务/服务层完成。"""
    return {"status": "completed"}


_PRIORITY = {"normal": "high", "boundary": "medium", "abnormal": "medium"}


def _deterministic_testcases(scenarios: list[dict], rule_index: dict) -> list[dict]:
    """用规则引擎为每个场景计算预期结果, 生成可执行的测试用例。"""
    engine = GroupingEngine(rule_index) if rule_index else None
    cases: list[dict] = []
    for idx, scenario in enumerate(scenarios, start=1):
        scenario_type = scenario.get("type", "normal")
        input_case = scenario.get("input", {})
        expected: dict = {}
        explanation = scenario.get("description", "")
        if engine and scenario_type != "abnormal":
            try:
                result = engine.group(input_case)
                expected = {
                    "mdc": result.get("mdc_code"),
                    "adrg": result.get("adrg_code"),
                    "drg": result.get("drg_code"),
                    "complication": result.get("complication"),
                }
            except Exception:  # noqa: BLE001
                expected = {}
        cases.append({
            "testCaseId": f"TC-D-{idx:03d}",
            "title": scenario.get("description", f"测试场景 {idx}"),
            "scenarioType": scenario_type,
            "priority": _PRIORITY.get(scenario_type, "medium"),
            "requirementRef": "FR-D-05",
            "inputCase": input_case,
            "expectedResult": expected,
            "expectedExplanation": explanation,
        })
    return cases

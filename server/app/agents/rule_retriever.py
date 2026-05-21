"""规则检索智能体 (规则 + LLM 辅助)。参照 plans/06_agent_workflow.md §2.3.4。"""

from __future__ import annotations

from app.agents.state import GroupingState
from app.engine.mdc_matcher import match_mdc


def validate_codes(state: GroupingState) -> dict:
    """编码校验节点 (规则)。对 parsed_case 做格式校验。"""
    from app.engine.code_validator import validate_case_codes

    case = state.get("parsed_case") or {}
    result = validate_case_codes(case)
    return {
        "validation_passed": result["is_valid"],
        "validation_errors": result["errors"],
        "validation_warnings": result["warnings"],
    }


def rule_retrieve_agent(state: GroupingState) -> dict:
    """根据病历编码从规则索引中检索候选规则 (确定性)。"""
    case = state.get("parsed_case") or {}
    rule_index = state.get("rule_index") or {}

    primary = (case.get("primaryDiagnosis") or {}).get("code")
    secondary = [d.get("code") for d in (case.get("secondaryDiagnoses") or []) if d.get("code")]

    mdc = match_mdc(primary, rule_index)
    mdc_candidates = [mdc["code"]] if mdc.get("code") else []

    adrg_candidates: list[str] = []
    if mdc.get("code"):
        adrg_candidates = list(rule_index.get("adrg_by_mdc", {}).get(mdc["code"], []))

    mcc_set = rule_index.get("mcc_set", set())
    cc_set = rule_index.get("cc_set", set())
    mcc_entries = [c for c in secondary if c in mcc_set or c in cc_set]

    return {
        "mdc_candidates": mdc_candidates,
        "adrg_candidates": adrg_candidates,
        "mcc_entries": mcc_entries,
    }

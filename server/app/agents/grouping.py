"""DRG 入组智能体 (规则引擎)。参照 plans/06_agent_workflow.md §2.3.5。

本节点是确定性逻辑, 不调用 LLM。
"""

from __future__ import annotations

from app.agents.state import GroupingState
from app.core.logging import logger
from app.engine.grouping_engine import GroupingEngine


def drg_group_agent(state: GroupingState) -> dict:
    """执行确定性 DRG 入组。"""
    case = state.get("parsed_case") or {}
    rule_index = state.get("rule_index") or {}

    try:
        engine = GroupingEngine(rule_index)
        result = engine.group(case)
    except Exception as exc:  # noqa: BLE001 - 引擎异常不应使工作流崩溃
        logger.exception(f"DRG 入组引擎异常: {exc}")
        return {
            "grouping_result": {
                "is_grouped": False,
                "stage": "rule_engine_error",
                "ungrouped_reason": f"规则引擎异常: {exc}",
                "evidence": [],
                "candidate_rules": [],
                "warnings": [],
            }
        }

    return {"grouping_result": result}

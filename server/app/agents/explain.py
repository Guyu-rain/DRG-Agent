"""解释生成智能体 (LLM)。参照 plans/06_agent_workflow.md §2.3.6。

将结构化证据链转换为自然语言。LLM 不可用时使用模板降级。
"""

from __future__ import annotations

import json

from app.agents.state import GroupingState
from app.llm import render_prompt


def _template_explanation(result: dict) -> str:
    """LLM 不可用时的模板化解释 (降级输出)。"""
    if result.get("is_grouped"):
        steps = "；".join(item.get("description", "") for item in result.get("evidence", []))
        return (
            f"病例进入 {result.get('mdc_code')}（{result.get('mdc_name')}），"
            f"匹配 ADRG {result.get('adrg_code')}（{result.get('adrg_name')}），"
            f"并发症等级为 {result.get('complication')}，"
            f"最终入组 DRG {result.get('drg_code')}（{result.get('drg_name')}）。"
            f"推理依据：{steps}。"
        )
    return (
        f"病例未能成功入组。失败阶段：{result.get('stage')}。"
        f"原因：{result.get('ungrouped_reason')}。"
        f"建议检查诊断/手术编码是否正确，或改用结构化输入补充信息。"
    )


def explain_agent(state: GroupingState) -> dict:
    """入组成功时生成解释文本。"""
    result = state.get("grouping_result") or {}
    llm = state.get("llm_client")
    fallback = _template_explanation(result)

    prompt = render_prompt(
        "explain_success",
        mdc_code=result.get("mdc_code"),
        mdc_name=result.get("mdc_name"),
        adrg_code=result.get("adrg_code"),
        adrg_name=result.get("adrg_name"),
        drg_code=result.get("drg_code"),
        drg_name=result.get("drg_name"),
        complication=result.get("complication"),
        evidence=json.dumps(result.get("evidence", []), ensure_ascii=False, indent=2),
    )
    explanation = llm.call_with_fallback(prompt, fallback_value=fallback) if llm else fallback
    return {"explanation": explanation or fallback, "status": "completed"}


def explain_failure_agent(state: GroupingState) -> dict:
    """入组失败时生成原因说明。"""
    result = state.get("grouping_result") or {}
    llm = state.get("llm_client")
    fallback = _template_explanation(result)

    prompt = render_prompt(
        "explain_failure",
        stage=result.get("stage", "unknown"),
        reason=result.get("ungrouped_reason", ""),
        mdc_code=result.get("mdc_code") or "无",
    )
    explanation = llm.call_with_fallback(prompt, fallback_value=fallback) if llm else fallback
    return {"explanation": explanation or fallback, "status": "completed"}

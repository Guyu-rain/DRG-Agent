"""病历解析智能体 (LLM)。参照 plans/06_agent_workflow.md §2.3.1。"""

from __future__ import annotations

from app.agents.state import GroupingState
from app.core.logging import logger
from app.llm import parse_llm_json_output, render_prompt


def case_parse_agent(state: GroupingState) -> dict:
    """将病历文本或结构化数据解析为标准化的 parsed_case。

    - 结构化输入: 直接采用 (服务层已完成中文字段映射与去重)。
    - 自由文本输入: 调用 LLM 提取结构化编码字段。
    """
    if state.get("structured_data"):
        return {"parsed_case": state["structured_data"], "status": "parsing"}

    raw_text = state.get("raw_text")
    if not raw_text:
        return {
            "parsed_case": None,
            "status": "error",
            "error": {"type": "EMPTY_INPUT", "message": "病历输入为空"},
        }

    llm = state.get("llm_client")
    prompt = render_prompt("case_parse", raw_text=raw_text)

    try:
        output = llm.call(prompt)
        parsed = parse_llm_json_output(output)
    except Exception as exc:  # noqa: BLE001 - LLM 失败降级
        logger.error(f"病历解析 LLM 调用失败: {exc}")
        parsed = None

    if not parsed or not isinstance(parsed, dict):
        return {
            "parsed_case": None,
            "status": "error",
            "error": {
                "type": "PARSE_FAILED",
                "message": "病历解析失败，建议改用结构化输入",
            },
        }

    # 将 LLM 输出的 patientInfo 展平
    patient_info = parsed.pop("patientInfo", {}) or {}
    parsed.setdefault("age", patient_info.get("age"))
    parsed.setdefault("gender", patient_info.get("gender"))
    return {"parsed_case": parsed, "status": "parsing"}

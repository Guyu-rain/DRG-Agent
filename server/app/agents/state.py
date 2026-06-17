"""LangGraph 工作流的 State 定义。参照 plans/06_agent_workflow.md §2.1/§3.1/§4.1。

非序列化的依赖 (llm_client / rule_index) 也作为 State 通道传递, 由编排器在初始
State 中注入, 仅在内存中存在。
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class GroupingState(TypedDict, total=False):
    """DRG 入组工作流状态。"""

    # 输入
    case_id: str
    rule_version_id: str
    raw_text: Optional[str]
    structured_data: Optional[dict]

    # 注入的依赖
    llm_client: Any
    rule_index: dict

    # 阶段产物
    parsed_case: Optional[dict]
    validation_passed: Optional[bool]
    validation_errors: list[str]
    validation_warnings: list[str]
    mdc_candidates: Optional[list]
    adrg_candidates: Optional[list]
    mcc_entries: Optional[list]
    grouping_result: Optional[dict]
    explanation: Optional[str]

    # 任务元数据
    task_id: Optional[str]
    status: str
    error: Optional[dict]


class DocumentGenState(TypedDict, total=False):
    """文档生成工作流状态。"""

    doc_type: str
    title: str
    context: dict
    template_name: Optional[str]

    llm_client: Any

    collected_context: Optional[dict]
    generated_content: Optional[str]
    formatted_content: Optional[str]

    doc_id: Optional[str]
    status: str
    error: Optional[str]


class TestGenState(TypedDict, total=False):
    """测试用例生成工作流状态。"""

    rule_version_id: str
    scenario_types: list[str]
    scope: dict
    sample_case_ids: list[str]
    max_count: int

    llm_client: Any
    rule_index: dict
    parsed_rules: dict

    rule_analysis: Optional[dict]
    scenarios: Optional[list]
    test_cases: Optional[list]
    sample_cases_data: list[dict]

    status: str
    error: Optional[str]

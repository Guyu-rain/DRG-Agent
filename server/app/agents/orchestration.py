"""智能体编排器 (AgentOrchestrator)。

参照 plans/06_agent_workflow.md §6。使用 LangGraph StateGraph 构建并执行三个
工作流: 入组、文档生成、测试用例生成。
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.case_parser import case_parse_agent
from app.agents.document_gen import (
    context_collect_agent,
    document_generate_agent,
    format_output_agent,
    generate_document_chat,
    generate_qa_answer,
    save_document_agent,
)
from app.agents.explain import explain_agent, explain_failure_agent
from app.agents.grouping import drg_group_agent
from app.agents.rule_retriever import rule_retrieve_agent, validate_codes
from app.agents.state import DocumentGenState, GroupingState, TestGenState
from app.agents.testcase_gen import (
    rule_analyze_agent,
    save_testcases_agent,
    scenario_construct_agent,
    testcase_generate_agent,
)
from app.core.logging import logger

# --- 条件路由 ----------------------------------------------------------------


def is_valid_route(state: GroupingState) -> Literal["rule_retrieve", "mark_as_error"]:
    """编码校验是否通过。"""
    return "rule_retrieve" if state.get("validation_passed") else "mark_as_error"


def is_grouped_route(state: GroupingState) -> Literal["explain", "explain_failure"]:
    """是否成功入组。"""
    result = state.get("grouping_result") or {}
    return "explain" if result.get("is_grouped") else "explain_failure"


# --- 辅助节点 ----------------------------------------------------------------


def mark_as_error(state: GroupingState) -> dict:
    """编码校验失败时的异常处理节点。"""
    errors = state.get("validation_errors") or ["未知校验错误"]
    return {
        "status": "failed",
        "grouping_result": {
            "is_grouped": False,
            "stage": "validation",
            "ungrouped_reason": "；".join(errors),
            "evidence": [],
            "candidate_rules": [],
            "warnings": state.get("validation_warnings") or [],
        },
        "error": {
            "type": "VALIDATION_FAILED",
            "stage": "validation",
            "message": "；".join(errors),
            "suggestions": ["检查诊断/手术编码格式", "尝试使用结构化输入"],
        },
    }


def save_result(state: GroupingState) -> dict:
    """工作流终点标记。实际落库由 GroupingService 完成。"""
    if state.get("status") not in ("failed", "completed"):
        return {"status": "completed"}
    return {}


class AgentOrchestrator:
    """管理所有 LangGraph 工作流的构建、编译与执行。"""

    def __init__(self, llm_client=None) -> None:
        self.llm_client = llm_client
        self._grouping_graph = None
        self._document_graph = None
        self._test_graph = None

    # ------------------------------------------------------------- 入组工作流
    def build_grouping_workflow(self):
        """构建 DRG 入组工作流。"""
        workflow = StateGraph(GroupingState)

        workflow.add_node("case_parse", case_parse_agent)
        workflow.add_node("validate", validate_codes)
        workflow.add_node("rule_retrieve", rule_retrieve_agent)
        workflow.add_node("drg_group", drg_group_agent)
        workflow.add_node("explain", explain_agent)
        workflow.add_node("explain_failure", explain_failure_agent)
        workflow.add_node("mark_as_error", mark_as_error)
        workflow.add_node("save_result", save_result)

        workflow.add_edge(START, "case_parse")
        workflow.add_edge("case_parse", "validate")
        workflow.add_conditional_edges(
            "validate",
            is_valid_route,
            {"rule_retrieve": "rule_retrieve", "mark_as_error": "mark_as_error"},
        )
        workflow.add_edge("rule_retrieve", "drg_group")
        workflow.add_conditional_edges(
            "drg_group",
            is_grouped_route,
            {"explain": "explain", "explain_failure": "explain_failure"},
        )
        workflow.add_edge("explain", "save_result")
        workflow.add_edge("explain_failure", "save_result")
        workflow.add_edge("mark_as_error", "save_result")
        workflow.add_edge("save_result", END)

        return workflow.compile()

    def execute_grouping(
        self,
        case_id: str,
        rule_version_id: str | None,
        rule_index: dict,
        raw_text: str | None = None,
        structured_data: dict | None = None,
    ) -> dict:
        """执行入组工作流, 返回最终 State。"""
        if self._grouping_graph is None:
            self._grouping_graph = self.build_grouping_workflow()

        initial: GroupingState = {
            "case_id": case_id,
            "rule_version_id": rule_version_id or "",
            "raw_text": raw_text,
            "structured_data": structured_data,
            "llm_client": self.llm_client,
            "rule_index": rule_index,
            "status": "executing",
            "validation_errors": [],
            "validation_warnings": [],
        }
        try:
            return self._grouping_graph.invoke(initial)
        except Exception as exc:  # noqa: BLE001 - 工作流异常不应使调用方崩溃
            logger.exception(f"入组工作流执行异常: {exc}")
            return {
                "status": "failed",
                "error": {"type": "WORKFLOW_ERROR", "message": str(exc)},
                "grouping_result": {
                    "is_grouped": False,
                    "stage": "workflow_error",
                    "ungrouped_reason": str(exc),
                    "evidence": [],
                    "candidate_rules": [],
                    "warnings": [],
                },
            }

    # --------------------------------------------------------- 文档生成工作流
    def build_document_gen_workflow(self):
        """构建文档生成工作流。"""
        workflow = StateGraph(DocumentGenState)
        workflow.add_node("context_collect", context_collect_agent)
        workflow.add_node("document_generate", document_generate_agent)
        workflow.add_node("format_output", format_output_agent)
        workflow.add_node("save_document", save_document_agent)

        workflow.add_edge(START, "context_collect")
        workflow.add_edge("context_collect", "document_generate")
        workflow.add_edge("document_generate", "format_output")
        workflow.add_edge("format_output", "save_document")
        workflow.add_edge("save_document", END)
        return workflow.compile()

    def execute_document_gen(
        self, doc_type: str, title: str, context: dict, template_name: str | None = None
    ) -> dict:
        """执行文档生成工作流, 返回最终 State。"""
        if self._document_graph is None:
            self._document_graph = self.build_document_gen_workflow()
        initial: DocumentGenState = {
            "doc_type": doc_type,
            "title": title,
            "context": context or {},
            "template_name": template_name,
            "llm_client": self.llm_client,
            "status": "running",
        }
        return self._document_graph.invoke(initial)

    def execute_document_chat(
        self,
        instruction: str,
        current_document: str = "",
        history: list[dict] | None = None,
        doc_type: str | None = None,
    ) -> str:
        """对话式生成/修订文档, 返回最新完整 Markdown 全文。"""
        return generate_document_chat(
            self.llm_client, instruction, current_document, history, doc_type
        )

    def execute_qa(
        self,
        instruction: str,
        history: list[dict] | None = None,
    ) -> str:
        """问答模式: 查阅源码回答技术问题, 不修改文档。"""
        return generate_qa_answer(self.llm_client, instruction, history)

    # ----------------------------------------------------- 测试用例生成工作流
    def build_test_gen_workflow(self):
        """构建测试用例生成工作流。"""
        workflow = StateGraph(TestGenState)
        workflow.add_node("rule_analyze", rule_analyze_agent)
        workflow.add_node("scenario_construct", scenario_construct_agent)
        workflow.add_node("testcase_generate", testcase_generate_agent)
        workflow.add_node("save_testcases", save_testcases_agent)

        workflow.add_edge(START, "rule_analyze")
        workflow.add_edge("rule_analyze", "scenario_construct")
        workflow.add_edge("scenario_construct", "testcase_generate")
        workflow.add_edge("testcase_generate", "save_testcases")
        workflow.add_edge("save_testcases", END)
        return workflow.compile()

    def execute_test_gen(
        self,
        rule_version_id: str | None,
        scenario_types: list[str],
        scope: dict,
        sample_case_ids: list[str],
        max_count: int,
        rule_index: dict,
        parsed_rules: dict,
    ) -> dict:
        """执行测试用例生成工作流, 返回最终 State。"""
        if self._test_graph is None:
            self._test_graph = self.build_test_gen_workflow()
        initial: TestGenState = {
            "rule_version_id": rule_version_id or "",
            "scenario_types": scenario_types,
            "scope": scope or {},
            "sample_case_ids": sample_case_ids or [],
            "max_count": max_count,
            "llm_client": self.llm_client,
            "rule_index": rule_index,
            "parsed_rules": parsed_rules,
            "status": "running",
        }
        return self._test_graph.invoke(initial)


_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """获取进程级共享的编排器 (注入默认 LLM 客户端)。"""
    global _orchestrator
    if _orchestrator is None:
        from app.llm import get_llm_client

        _orchestrator = AgentOrchestrator(llm_client=get_llm_client())
    return _orchestrator

"""文档生成智能体 (LLM + 模板)。参照 plans/06_agent_workflow.md §3。"""

from __future__ import annotations

import json

from app.agents.state import DocumentGenState
from app.core.logging import logger
from app.llm import render_prompt

# doc_type -> prompt 模板名
_TEMPLATE_MAP = {
    "requirements": "document_srs",
    "design": "document_design",
    "testing": "document_test",
}


def context_collect_agent(state: DocumentGenState) -> dict:
    """收集文档生成所需上下文。

    数据库相关上下文由服务层预先收集并通过 state['context'] 传入,
    本节点负责补充系统级静态信息。
    """
    context = dict(state.get("context") or {})
    context.setdefault("system_description", "DRG-Agent 医保 DRG 入组智能体系统")
    context.setdefault(
        "modules",
        ["DRG 入组", "文档自动生成", "测试用例生成", "虚拟文档系统"],
    )
    context.setdefault("doc_type", state.get("doc_type"))
    return {"collected_context": context}


def document_generate_agent(state: DocumentGenState) -> dict:
    """调用 LLM 根据模板与上下文生成文档内容。"""
    doc_type = state.get("doc_type", "requirements")
    title = state.get("title", "DRG-Agent 文档")
    context = state.get("collected_context") or {}
    llm = state.get("llm_client")

    template_name = _TEMPLATE_MAP.get(doc_type, "document_srs")
    fallback = _template_document(doc_type, title, context)

    try:
        prompt = render_prompt(
            template_name,
            title=title,
            context=json.dumps(context, ensure_ascii=False, indent=2, default=str),
        )
        content = llm.call_with_fallback(prompt, fallback_value=fallback) if llm else fallback
    except Exception as exc:  # noqa: BLE001
        logger.error(f"文档生成失败, 使用模板降级: {exc}")
        content = fallback

    return {"generated_content": content or fallback, "status": "running"}


def format_output_agent(state: DocumentGenState) -> dict:
    """将生成内容格式化为标准 Markdown (补充标题)。"""
    content = state.get("generated_content") or ""
    title = state.get("title", "DRG-Agent 文档")
    if not content.lstrip().startswith("#"):
        content = f"# {title}\n\n{content}"
    return {"formatted_content": content}


def save_document_agent(state: DocumentGenState) -> dict:
    """工作流结束标记。实际落库由 Celery 任务/服务层完成。"""
    return {"status": "completed"}


def _template_document(doc_type: str, title: str, context: dict) -> str:
    """LLM 不可用时的模板化文档 (降级输出)。"""
    type_label = {
        "requirements": "需求分析文档",
        "design": "概要设计文档",
        "testing": "测试文档",
        "management": "项目管理文档",
        "configuration": "配置管理文档",
        "meeting_minutes": "会议纪要",
    }.get(doc_type, "工程文档")
    modules = "、".join(context.get("modules", []))
    return (
        f"# {title}\n\n"
        f"> 文档类型：{type_label}（模板化降级生成）\n\n"
        f"## 1. 概述\n\n{context.get('system_description', 'DRG-Agent 系统')}。\n\n"
        f"系统包含以下模块：{modules}。\n\n"
        f"## 2. 内容\n\n本文档由文档生成智能体在 LLM 不可用时按模板生成，"
        f"可在虚拟文档系统中进一步编辑完善。\n\n"
        f"## 3. 上下文摘要\n\n```json\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2, default=str)}\n```\n"
    )

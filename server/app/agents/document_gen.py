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

# doc_type -> 对话式生成的结构性提示
_TYPE_HINT = {
    "requirements": "本次文档类型为《需求分析文档（SRS）》，建议涵盖引言、总体描述、"
    "功能需求（带编号如 FR-01）、非功能需求、用例说明、分析模型。\n\n",
    "design": "本次文档类型为《概要设计文档》，建议涵盖架构设计、模块划分、"
    "接口设计、数据库设计、关键类设计。\n\n",
    "testing": "本次文档类型为《测试文档》，建议涵盖测试策略、测试范围、"
    "测试用例（区分正常/边界/异常）、缺陷记录、覆盖率说明。\n\n",
    "management": "本次文档类型为《项目管理文档》，建议涵盖项目计划、里程碑、"
    "风险管理、过程记录。\n\n",
    "configuration": "本次文档类型为《配置管理文档》，建议涵盖配置项标识、"
    "版本控制策略、变更流程、基线管理。\n\n",
}


def generate_document_chat(
    llm_client,  # noqa: ANN001
    instruction: str,
    current_document: str = "",
    history: list[dict] | None = None,
    doc_type: str | None = None,
) -> str:
    """对话式生成/修订文档, 返回最新完整 Markdown 全文。

    Args:
        llm_client: LLM 客户端 (可为 None, 此时走降级)。
        instruction: 本轮用户指令。
        current_document: 当前文档全文 (空表示新建)。
        history: 既往对话消息 [{"role", "content"}, ...] (不含本轮 instruction)。
        doc_type: 可选文档类型标签, 用于补充结构性提示。
    """
    system_prompt = render_prompt(
        "document_chat",
        type_hint=_TYPE_HINT.get(doc_type or "", ""),
        current_document=current_document or "（空）",
    )
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history or []:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": instruction})

    fallback = _chat_fallback(instruction, current_document, doc_type)
    if llm_client is None:
        return fallback
    try:
        content = llm_client.call(prompt=instruction, messages=messages, max_tokens=6000)
        return content.strip() or fallback
    except Exception as exc:  # noqa: BLE001
        logger.error(f"对话式文档生成失败, 使用降级输出: {exc}")
        return fallback


def _chat_fallback(instruction: str, current_document: str, doc_type: str | None) -> str:
    """LLM 不可用时的降级: 在现有文档后追加用户指令记录。"""
    if current_document.strip():
        return (
            f"{current_document.rstrip()}\n\n"
            f"## 待办（LLM 暂不可用，已记录指令）\n\n- {instruction}\n"
        )
    type_label = {
        "requirements": "需求分析文档", "design": "概要设计文档", "testing": "测试文档",
        "management": "项目管理文档", "configuration": "配置管理文档",
    }.get(doc_type or "", "工程文档")
    return (
        f"# {type_label}\n\n> LLM 暂不可用，以下为根据指令生成的占位草稿。\n\n"
        f"## 需求\n\n{instruction}\n\n## 内容\n\n待 LLM 恢复后可继续对话完善本文档。\n"
    )


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

"""文档系统相关 Pydantic Schema。参照 plans/03_api_interfaces.md §5。"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class DocumentGenerateRequest(CamelModel):
    doc_type: str = Field(description="requirements | design | testing | meeting_minutes | configuration")
    title: str
    context: dict[str, Any] = {}
    template: str | None = None


class DocumentEditRequest(CamelModel):
    content: str | None = None
    title: str | None = None


class DocumentStatusUpdate(CamelModel):
    status: str = Field(description="draft | review | submitted | archived")


class ConversationCreateRequest(CamelModel):
    title: str | None = None
    doc_type: str | None = Field(default=None, description="可选文档类型标签")


class MessageSendRequest(CamelModel):
    instruction: str = Field(description="本轮对用户文档的指令 (新建/扩写/修订等)")


class QaSendRequest(CamelModel):
    instruction: str = Field(description="用户的技术问题")


class ReasoningStep(CamelModel):
    id: str
    title: str
    detail: str | None = None
    status: str = Field(description="pending | running | completed | failed")


class ReasoningSummary(CamelModel):
    status: str = Field(description="thinking | completed | failed")
    steps: list[ReasoningStep] = Field(default_factory=list)


class QaMessage(CamelModel):
    message_id: str
    role: str
    content: str
    reasoning_summary: ReasoningSummary | None = None
    created_at: str


class QaSendResponse(CamelModel):
    assistant_message: QaMessage
    conversation_id: str | None = None


class DocumentSection(CamelModel):
    id: str
    title: str
    status: str = "generated"


class DocumentTaskResponse(CamelModel):
    doc_task_id: str
    status: str
    created_at: Any | None = None
    result_doc_id: str | None = None


class DocumentSummary(CamelModel):
    doc_id: str
    title: str
    type: str
    status: str
    version: str = "V1.0"
    created_at: Any | None = None
    submitted_at: Any | None = None
    generated_by: str | None = None
    file_size: int | None = None


class DocumentDetail(CamelModel):
    doc_id: str
    title: str
    type: str
    version: str = "V1.0"
    status: str
    content: str = ""
    metadata: dict[str, Any] | None = None
    sections: list[dict] = []


class DocumentPreviewResponse(DocumentDetail):
    """文档预览, 字段同详情。"""

"""文档相关 ORM 模型。参照 plans/05_data_model.md §2.8-2.10。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, generate_id, utcnow


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "DOC"))
    doc_type = Column(String(30), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")
    original_content = Column(Text, nullable=True)

    version = Column(String(20), nullable=False, default="V1.0")
    status = Column(String(20), nullable=False, default="draft", index=True)

    author = Column(String(80), nullable=True)
    generated_by = Column(String(80), nullable=True)

    metadata_json = Column(JSON, nullable=True)
    source_task_id = Column(String(48), nullable=True)

    file_path = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(80), nullable=True)

    sections = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.created_at",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "DOCVER"))
    document_id = Column(String(40), ForeignKey("documents.id"), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    content_snapshot = Column(Text, nullable=False, default="")
    change_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    created_by = Column(String(80), nullable=True)

    document = relationship("Document", back_populates="versions")


class DocumentConversation(Base):
    """文档生成会话。一个会话围绕一篇文档进行多轮对话式迭代。"""

    __tablename__ = "document_conversations"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "CONV"))
    title = Column(String(255), nullable=False, default="新文档对话")
    doc_type = Column(String(30), nullable=True)  # 可选标签, 由用户选择或对话推断
    mode = Column(String(20), nullable=False, default="doc_chat", index=True)  # doc_chat | qa
    document_id = Column(String(40), ForeignKey("documents.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages = relationship(
        "DocumentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="DocumentMessage.created_at",
    )
    document = relationship("Document")


class DocumentMessage(Base):
    """会话中的一条消息 (用户指令或助手回复)。"""

    __tablename__ = "document_messages"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "MSG"))
    conversation_id = Column(
        String(40), ForeignKey("document_conversations.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False, default="")
    doc_version = Column(String(20), nullable=True)  # 该回复产出的文档版本
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    conversation = relationship("DocumentConversation", back_populates="messages")


class DocumentTask(Base):
    __tablename__ = "document_tasks"

    id = Column(String(48), primary_key=True, default=partial(generate_id, "DOC-TASK"))
    doc_type = Column(String(30), nullable=False)
    title = Column(String(255), nullable=False)
    context = Column(JSON, nullable=True)
    template = Column(String(80), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    result_doc_id = Column(String(40), ForeignKey("documents.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

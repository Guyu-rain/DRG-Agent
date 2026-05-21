"""执行日志 (ExecutionLog) ORM 模型。参照 plans/05_data_model.md §2.13。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Column, DateTime, String, Text

from app.models.base import Base, generate_id, utcnow


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "LOG"))
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    level = Column(String(10), nullable=False, default="info", index=True)
    agent = Column(String(50), nullable=True)
    task_id = Column(String(48), nullable=True, index=True)
    message = Column(Text, nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

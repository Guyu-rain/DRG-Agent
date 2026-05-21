"""入组任务相关 ORM 模型。参照 plans/05_data_model.md §2.5-2.7。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, generate_id, utcnow


class GroupingTask(Base):
    __tablename__ = "grouping_tasks"

    id = Column(String(48), primary_key=True, default=partial(generate_id, "TASK-GROUP"))
    case_id = Column(String(40), ForeignKey("patient_cases.id"), nullable=False, index=True)
    rule_version_id = Column(String(40), ForeignKey("rule_versions.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    priority = Column(Integer, nullable=False, default=0)

    input_snapshot = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    created_by = Column(String(50), nullable=True)

    case = relationship("PatientCase", back_populates="grouping_tasks")
    result = relationship(
        "GroupingResult", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )
    steps = relationship(
        "TaskStep", back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_order"
    )


class GroupingResult(Base):
    __tablename__ = "grouping_results"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "GR"))
    task_id = Column(String(48), ForeignKey("grouping_tasks.id"), nullable=False, unique=True)

    mdc_code = Column(String(20), nullable=True)
    mdc_name = Column(String(200), nullable=True)
    adrg_code = Column(String(20), nullable=True)
    adrg_name = Column(String(200), nullable=True)
    drg_code = Column(String(20), nullable=True, index=True)
    drg_name = Column(String(200), nullable=True)

    is_grouped = Column(Boolean, nullable=False, default=False)
    ungrouped_reason = Column(Text, nullable=True)

    complication = Column(String(10), nullable=True)
    evidence_chain = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)

    candidate_rules = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)

    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    task = relationship("GroupingTask", back_populates="result")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "STEP"))
    task_id = Column(String(48), ForeignKey("grouping_tasks.id"), nullable=False, index=True)
    step_name = Column(String(40), nullable=False)
    step_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    task = relationship("GroupingTask", back_populates="steps")

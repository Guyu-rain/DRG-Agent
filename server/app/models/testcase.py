"""测试用例相关 ORM 模型。参照 plans/05_data_model.md §2.11-2.12。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base, generate_id, utcnow


class TestTask(Base):
    __tablename__ = "test_tasks"

    id = Column(String(48), primary_key=True, default=partial(generate_id, "TEST-TASK"))
    rule_version_id = Column(String(40), ForeignKey("rule_versions.id"), nullable=True)
    scenario_types = Column(JSON, nullable=True)
    scope = Column(JSON, nullable=True)
    sample_case_ids = Column(JSON, nullable=True)
    max_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    generated_count = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "TC"))
    test_task_id = Column(String(48), ForeignKey("test_tasks.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    scenario_type = Column(String(20), nullable=False, index=True)
    priority = Column(String(20), nullable=False, default="medium")

    requirement_ref = Column(String(40), nullable=True, index=True)
    rule_version_id = Column(String(40), ForeignKey("rule_versions.id"), nullable=True)

    input_case = Column(JSON, nullable=True)
    expected_result = Column(JSON, nullable=True)
    expected_explanation = Column(Text, nullable=True)

    actual_result = Column(JSON, nullable=True)
    is_passed = Column(Boolean, nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    created_by = Column(String(80), nullable=True)

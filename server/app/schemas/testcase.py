"""测试用例相关 Pydantic Schema。参照 plans/03_api_interfaces.md §6。"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class TestGenScope(CamelModel):
    mdc_list: list[str] = []
    adrg_list: list[str] = []
    include_all_rules: bool = False


class TestGenRequest(CamelModel):
    rule_version_id: str | None = None
    scenario_types: list[str] = ["normal", "boundary", "abnormal"]
    scope: TestGenScope = Field(default_factory=TestGenScope)
    sample_case_ids: list[str] = []
    max_count: int = 50


class TestTaskResponse(CamelModel):
    test_task_id: str
    status: str
    created_at: Any | None = None
    generated_count: int | None = None


class TestCaseSummary(CamelModel):
    test_case_id: str
    title: str
    scenario_type: str
    priority: str
    requirement_ref: str | None = None
    rule_version: str | None = None
    input_case: dict[str, Any] | None = None
    expected_result: dict[str, Any] | None = None
    expected_explanation: str | None = None
    created_at: Any | None = None


class TestCaseDetail(TestCaseSummary):
    actual_result: dict[str, Any] | None = None
    is_passed: bool | None = None


class TestExportRequest(CamelModel):
    test_case_ids: list[str]
    format: str = "excel"


class TestSubmitRequest(CamelModel):
    test_case_ids: list[str]
    doc_title: str
    doc_type: str = "testing"

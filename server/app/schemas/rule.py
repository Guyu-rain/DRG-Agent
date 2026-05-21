"""规则管理相关 Pydantic Schema。参照 plans/03_api_interfaces.md §3。"""

from __future__ import annotations

from typing import Any

from app.schemas.common import CamelModel


class MDCSchema(CamelModel):
    code: str
    name: str | None = None
    icd_prefixes: list[str] = []


class ADRGSchema(CamelModel):
    code: str
    name: str | None = None
    mdc: str | None = None
    surgery_list: list[str] = []
    diagnosis_list: list[str] = []


class DRGSchema(CamelModel):
    code: str
    name: str | None = None
    adrg: str | None = None
    cc_level: str | None = None


class CCMCCEntrySchema(CamelModel):
    code: str
    name: str | None = None
    level: str | None = None


class RuleImportRequest(CamelModel):
    """规则导入的表单元数据 (文件本身通过 multipart 上传)。"""

    version_name: str
    description: str | None = None


class RuleVersionSummary(CamelModel):
    version_id: str
    version_name: str
    description: str | None = None
    status: str
    rule_count: dict[str, int] | None = None
    imported_at: Any | None = None
    is_active: bool = False


class RuleVersionDetail(CamelModel):
    version_id: str
    version_name: str
    description: str | None = None
    status: str
    mdc_list: list[dict] = []
    adrg_list: list[dict] = []
    drg_list: list[dict] = []
    mcc_list: list[dict] = []
    cc_list: list[dict] = []
    exclusion_table: list[dict] = []
    rule_count: dict[str, int] | None = None

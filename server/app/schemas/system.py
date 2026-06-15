"""系统配置相关 Pydantic Schema。参照 plans/03_api_interfaces.md §8。"""

from __future__ import annotations

from app.schemas.common import CamelModel


class LLMConfigSchema(CamelModel):
    api_base: str | None = None
    model: str | None = None
    max_retries: int = 3
    timeout_seconds: int | None = None


class StorageConfigSchema(CamelModel):
    document_path: str | None = None
    rule_data_path: str | None = None


class RulesConfigSchema(CamelModel):
    active_rule_version_id: str | None = None


class SystemConfigResponse(CamelModel):
    llm: LLMConfigSchema
    storage: StorageConfigSchema
    rules: RulesConfigSchema


class SystemConfigUpdate(CamelModel):
    llm: LLMConfigSchema | None = None
    storage: StorageConfigSchema | None = None


class DemoInitResponse(CamelModel):
    rule_version_id: str
    sample_case_ids: list[str] = []
    message: str = "演示数据初始化成功"


class HealthCheckResponse(CamelModel):
    status: str
    components: dict[str, str]
    uptime: str | None = None

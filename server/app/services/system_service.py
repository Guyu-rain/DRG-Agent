"""系统配置与演示数据服务层。参照 plans/03_api_interfaces.md §8。"""

from __future__ import annotations

import asyncio
import json
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models import PatientCase, RuleVersion, SystemConfig
from app.services.case_service import CaseService
from app.services.rule_service import RuleService

_START_TIME = time.time()

# 课程示例病历 (A01.002+G01* -> BB11)
_COURSE_SAMPLE = {
    "性别": "男",
    "年龄": 45,
    "主要诊断": {"疾病名称": "伤寒性脑膜炎", "疾病编码": "A01.002+G01*"},
    "次要诊断列表": [{"疾病名称": "急性呼吸衰竭", "疾病编码": "J96.0"}],
    "主要手术": {"手术名称": "动脉内膜剥脱术", "手术编码": "38.1000x002", "手术级别": 3},
    "其他手术列表": [],
}


class SystemService:
    """系统配置读写、演示数据初始化、健康检查。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_or_create_config(self) -> SystemConfig:
        config = await self.db.get(SystemConfig, 1)
        if config is None:
            config = SystemConfig(
                id=1,
                llm_config={
                    "api_base": settings.LLM_API_BASE,
                    "model": settings.LLM_MODEL,
                    "max_retries": settings.LLM_MAX_RETRIES,
                    "timeout": None,
                },
                storage_config={
                    "document_path": settings.DOCUMENT_STORAGE_PATH,
                    "rule_data_path": settings.RULE_DATA_PATH,
                },
                demo_initialized=False,
            )
            self.db.add(config)
            await self.db.flush()
        return config

    async def get_config(self) -> dict:
        config = await self._get_or_create_config()
        llm = config.llm_config or {}
        storage = config.storage_config or {}
        return {
            "llm": {
                "apiBase": llm.get("api_base"),
                "model": llm.get("model"),
                "maxRetries": llm.get("max_retries", 3),
                "timeoutSeconds": None,
            },
            "storage": {
                "documentPath": storage.get("document_path"),
                "ruleDataPath": storage.get("rule_data_path"),
            },
            "rules": {"activeRuleVersionId": config.active_rule_version_id},
        }

    async def update_config(self, payload: dict) -> dict:
        config = await self._get_or_create_config()
        llm = payload.get("llm")
        if llm:
            current = dict(config.llm_config or {})
            if llm.get("apiBase") is not None:
                current["api_base"] = llm["apiBase"]
            if llm.get("model") is not None:
                current["model"] = llm["model"]
            if llm.get("maxRetries") is not None:
                current["max_retries"] = llm["maxRetries"]
            current["timeout"] = None
            config.llm_config = current
        storage = payload.get("storage")
        if storage:
            current = dict(config.storage_config or {})
            if storage.get("documentPath") is not None:
                current["document_path"] = storage["documentPath"]
            if storage.get("ruleDataPath") is not None:
                current["rule_data_path"] = storage["ruleDataPath"]
            config.storage_config = current
        await self.db.flush()
        return await self.get_config()

    async def init_demo_data(self) -> dict:
        """一键初始化演示数据 (规则 + 样例病历)。幂等。"""
        config = await self._get_or_create_config()
        if config.demo_initialized:
            version = (
                await self.db.execute(select(RuleVersion).where(RuleVersion.status == "active").limit(1))
            ).scalar_one_or_none()
            case_ids = list(
                (await self.db.execute(select(PatientCase.id).limit(10))).scalars().all()
            )
            return {
                "ruleVersionId": version.id if version else None,
                "sampleCaseIds": case_ids,
                "message": "演示数据已存在 (幂等返回)",
            }

        rule_service = RuleService(self.db)
        version = await rule_service.import_demo_rules()
        await rule_service.activate_version(version.id)

        case_service = CaseService(self.db)
        sample_cases = [_COURSE_SAMPLE]
        example_path = settings.repo_root / "example" / "drg_example.json"
        if example_path.exists():
            try:
                sample_cases.extend(json.loads(example_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning(f"读取 example/drg_example.json 失败: {exc}")

        created = await case_service.import_from_example(sample_cases)
        config.demo_initialized = True
        config.active_rule_version_id = version.id
        await self.db.flush()

        logger.info(f"演示数据初始化完成: 规则版本 {version.id}, {len(created)} 个样例病历")
        return {
            "ruleVersionId": version.id,
            "sampleCaseIds": [c.id for c in created],
            "message": "演示数据初始化成功",
        }

    async def health_check(self) -> dict:
        """系统健康检查。"""
        components: dict[str, str] = {}

        try:
            await self.db.execute(select(func.count()).select_from(SystemConfig))
            components["database"] = "connected"
        except Exception:  # noqa: BLE001
            components["database"] = "disconnected"

        components["redis"] = await self._check_redis()
        components["celery"] = await self._check_celery()

        try:
            storage = settings.document_storage_dir
            storage.mkdir(parents=True, exist_ok=True)
            components["document_storage"] = "available"
        except OSError:
            components["document_storage"] = "unavailable"

        components["llm_api"] = "configured" if settings.LLM_API_KEY else "not_configured"

        healthy = components["database"] == "connected"
        uptime_s = int(time.time() - _START_TIME)
        return {
            "status": "healthy" if healthy else "degraded",
            "components": components,
            "uptime": f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m",
        }

    @staticmethod
    async def _check_redis() -> str:
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await client.ping()
            await client.aclose()
            return "connected"
        except Exception:  # noqa: BLE001
            return "disconnected"

    @staticmethod
    async def _check_celery() -> str:
        if settings.TASKS_EAGER:
            return "eager"
        try:
            from app.tasks import celery_app

            replies = await asyncio.to_thread(
                lambda: celery_app.control.inspect(timeout=1).ping()
            )
            return "running" if replies else "unavailable"
        except Exception:  # noqa: BLE001
            return "unavailable"

"""规则管理服务层。参照 plans/03_api_interfaces.md §3。"""

from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, ErrorCode, NotFoundException
from app.core.logging import logger
from app.engine.rule_parser import build_rule_index, count_rules, parse_rule_file
from app.models import GroupingTask, RuleVersion, utcnow


def parsed_rules_from_version(version: RuleVersion) -> dict:
    """从 RuleVersion 还原解析后的规则字典。"""
    return {
        "mdc_list": version.mdc_list or [],
        "adrg_list": version.adrg_list or [],
        "drg_list": version.drg_list or [],
        "mcc_list": version.mcc_list or [],
        "cc_list": version.cc_list or [],
        "exclusion_table": version.exclusion_table or [],
    }


def index_from_version(version: RuleVersion) -> dict:
    """从 RuleVersion 构建内存规则索引。"""
    return build_rule_index(parsed_rules_from_version(version))


class RuleService:
    """规则版本的导入、激活、查询与删除。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_rules(
        self, file_bytes: bytes, filename: str, version_name: str, description: str | None = None
    ) -> RuleVersion:
        """导入规则文件并解析为结构化规则版本。"""
        rule_dir = settings.rule_data_dir
        rule_dir.mkdir(parents=True, exist_ok=True)
        file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
        suffix = filename[filename.rfind(".") :] if "." in filename else ".json"
        stored_path = rule_dir / f"import_{file_hash}{suffix}"
        stored_path.write_bytes(file_bytes)

        parsed = parse_rule_file(stored_path)
        status = "error" if parsed["parse_errors"] and not parsed["mdc_list"] else "imported"
        version = RuleVersion(
            version_name=version_name,
            description=description,
            source_filename=filename,
            source_file_hash=file_hash,
            status=status,
            parse_errors=parsed["parse_errors"],
            mdc_list=parsed["mdc_list"],
            adrg_list=parsed["adrg_list"],
            drg_list=parsed["drg_list"],
            mcc_list=parsed["mcc_list"],
            cc_list=parsed["cc_list"],
            exclusion_table=parsed["exclusion_table"],
            rule_counts=count_rules(parsed),
        )
        self.db.add(version)
        await self.db.flush()
        logger.info(f"规则版本已导入: {version.id} ({version_name}) status={status}")
        return version

    async def import_demo_rules(self, version_name: str = "DRG 2.0 演示规则") -> RuleVersion:
        """导入内置演示规则文件 (server/data/rules/demo_rules.json)。"""
        demo_path = settings.rule_data_dir / "demo_rules.json"
        return await self.import_rules(
            demo_path.read_bytes(), "demo_rules.json", version_name, "课程演示用内置规则集"
        )

    async def get_versions(self) -> list[RuleVersion]:
        stmt = select(RuleVersion).order_by(RuleVersion.imported_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_version(self, version_id: str) -> RuleVersion:
        version = await self.db.get(RuleVersion, version_id)
        if version is None:
            raise NotFoundException(
                ErrorCode.RULE_VERSION_NOT_FOUND, f"规则版本不存在: {version_id}"
            )
        return version

    async def get_active_version(self) -> RuleVersion | None:
        stmt = select(RuleVersion).where(RuleVersion.status == "active").limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def activate_version(self, version_id: str) -> RuleVersion:
        """激活规则版本 (同一时刻仅一个 active)。"""
        target = await self.get_version(version_id)
        stmt = select(RuleVersion).where(RuleVersion.status == "active")
        for current in (await self.db.execute(stmt)).scalars().all():
            current.status = "archived"
            current.archived_at = utcnow()
        target.status = "active"
        target.activated_at = utcnow()
        await self.db.flush()

        # 同步系统配置
        from app.models import SystemConfig

        config = await self.db.get(SystemConfig, 1)
        if config is not None:
            config.active_rule_version_id = version_id
        logger.info(f"规则版本已激活: {version_id}")
        return target

    async def rename_version(self, version_id: str, version_name: str) -> RuleVersion:
        """重命名规则版本，不改变版本 ID、状态或规则内容。"""
        version = await self.get_version(version_id)
        normalized_name = version_name.strip()
        if not normalized_name:
            raise BadRequestException(ErrorCode.REQUIRED_FIELD_MISSING, "规则版本名称不能为空")
        version.version_name = normalized_name
        await self.db.flush()
        logger.info(f"规则版本已重命名: {version_id} -> {normalized_name}")
        return version

    async def delete_version(self, version_id: str) -> None:
        """删除规则版本。活跃版本或被入组任务引用的版本不可删除。"""
        version = await self.get_version(version_id)
        if version.status == "active":
            raise ConflictException(
                ErrorCode.RESOURCE_IN_USE, "活跃版本不可删除，请先激活其他版本"
            )
        ref_count = (
            await self.db.execute(
                select(func.count()).select_from(GroupingTask).where(
                    GroupingTask.rule_version_id == version_id
                )
            )
        ).scalar_one()
        if ref_count > 0:
            raise ConflictException(
                ErrorCode.RESOURCE_IN_USE,
                f"规则版本被 {ref_count} 个入组任务引用，无法删除",
            )
        await self.db.delete(version)
        await self.db.flush()

    async def search_rules(self, code: str, rule_type: str | None = None) -> list[dict]:
        """按编码在活跃版本中检索规则。"""
        version = await self.get_active_version()
        if version is None:
            return []
        matches: list[dict] = []

        if rule_type in (None, "mdc"):
            for mdc in version.mdc_list or []:
                hit = next((p for p in mdc.get("icd_prefixes", []) if code.startswith(p)), None)
                if hit:
                    matches.append({
                        "ruleType": "mdc",
                        "code": mdc["code"],
                        "name": mdc.get("name"),
                        "matchedBy": f"诊断编码 {code} 命中前缀 {hit}",
                    })
        if rule_type in (None, "adrg"):
            for adrg in version.adrg_list or []:
                if code in (adrg.get("surgery_list") or []):
                    matches.append({
                        "ruleType": "adrg",
                        "code": adrg["code"],
                        "name": adrg.get("name"),
                        "matchedBy": f"手术编码 {code} 命中 ADRG 手术列表",
                    })
        if rule_type in (None, "drg"):
            for drg in version.drg_list or []:
                if drg.get("code") == code:
                    matches.append({
                        "ruleType": "drg",
                        "code": drg["code"],
                        "name": drg.get("name"),
                        "matchedBy": "DRG 编码精确匹配",
                    })
        return matches

    # --------------------------------------------------------------- 序列化
    @staticmethod
    def to_summary(version: RuleVersion) -> dict:
        return {
            "versionId": version.id,
            "versionName": version.version_name,
            "description": version.description,
            "status": version.status,
            "ruleCount": version.rule_counts,
            "importedAt": version.imported_at,
            "isActive": version.status == "active",
        }

    @staticmethod
    def to_detail(version: RuleVersion) -> dict:
        """规则版本详情。将内部 snake_case 规则字段归一化为接口 camelCase。"""
        return {
            "versionId": version.id,
            "versionName": version.version_name,
            "description": version.description,
            "status": version.status,
            "isActive": version.status == "active",
            "importedAt": version.imported_at,
            "mdcList": [
                {"code": m.get("code"), "name": m.get("name"), "icdPrefix": m.get("icd_prefixes", [])}
                for m in (version.mdc_list or [])
            ],
            "adrgList": [
                {
                    "code": a.get("code"),
                    "name": a.get("name"),
                    "mdc": a.get("mdc"),
                    "surgeryList": a.get("surgery_list", []),
                    "diagnosisList": a.get("diagnosis_list", []),
                }
                for a in (version.adrg_list or [])
            ],
            "drgList": [
                {"code": d.get("code"), "name": d.get("name"), "adrg": d.get("adrg"), "ccLevel": d.get("cc_level")}
                for d in (version.drg_list or [])
            ],
            "mccList": version.mcc_list or [],
            "ccList": version.cc_list or [],
            "exclusionTable": [
                {"diagCode": e.get("diag_code"), "excludedBy": e.get("excluded_by", [])}
                for e in (version.exclusion_table or [])
            ],
            "ruleCount": version.rule_counts,
            "parseErrors": version.parse_errors or [],
        }

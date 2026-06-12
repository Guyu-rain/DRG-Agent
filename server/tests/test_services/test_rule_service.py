"""规则服务层测试。"""

import pytest
from app.core.exceptions import ConflictException, NotFoundException
from app.services.rule_service import RuleService


async def test_import_and_activate_demo_rules(db_session):
    service = RuleService(db_session)
    version = await service.import_demo_rules()
    assert version.status == "imported"
    assert version.rule_counts["mdc"] >= 1

    activated = await service.activate_version(version.id)
    assert activated.status == "active"


async def test_only_one_active_version(db_session):
    service = RuleService(db_session)
    v1 = await service.import_demo_rules("规则 A")
    v2 = await service.import_demo_rules("规则 B")
    await service.activate_version(v1.id)
    await service.activate_version(v2.id)
    await db_session.refresh(v1)
    assert v1.status == "archived"
    assert (await service.get_active_version()).id == v2.id


async def test_rename_version_preserves_identity_and_status(db_session):
    service = RuleService(db_session)
    version = await service.import_demo_rules("原名称")
    await service.activate_version(version.id)

    renamed = await service.rename_version(version.id, "  新规则名称  ")

    assert renamed.id == version.id
    assert renamed.version_name == "新规则名称"
    assert renamed.status == "active"


async def test_delete_active_version_blocked(db_session):
    service = RuleService(db_session)
    version = await service.import_demo_rules()
    await service.activate_version(version.id)
    with pytest.raises(ConflictException):
        await service.delete_version(version.id)


async def test_get_version_not_found(db_session):
    service = RuleService(db_session)
    with pytest.raises(NotFoundException):
        await service.get_version("RV-NOPE")


async def test_search_rules(db_session):
    service = RuleService(db_session)
    version = await service.import_demo_rules()
    await service.activate_version(version.id)
    matches = await service.search_rules("A01.002", "mdc")
    assert any(m["code"] == "MDCB" for m in matches)

"""病历服务层测试。"""

import json
from pathlib import Path

import pytest
from app.services.case_service import CaseService

_EXAMPLE = Path(__file__).resolve().parents[3] / "example" / "drg_example.json"


def test_normalize_chinese_keys():
    data = {
        "性别": "男",
        "年龄": 72,
        "主要诊断": {"疾病名称": "胃窦恶性肿瘤", "疾病编码": "C16.301"},
        "次要诊断列表": [{"疾病名称": "肠粘连", "疾病编码": "K66.002"}],
        "主要手术": {"手术名称": "胃大部切除术", "手术编码": "43.7x03", "手术级别": 3},
    }
    out = CaseService._normalize_case_input(data)
    assert out["gender"] == "男"
    assert out["primaryDiagnosis"]["code"] == "C16.301"
    assert out["primaryProcedure"]["level"] == 3


def test_normalize_dedups_procedures():
    data = {
        "主要诊断": {"疾病名称": "x", "疾病编码": "A01"},
        "其他手术列表": [
            {"手术名称": "穿刺", "手术编码": "34.9103"},
            {"手术名称": "穿刺", "手术编码": "34.9103"},  # 重复
        ],
    }
    out = CaseService._normalize_case_input(data)
    assert len(out["otherProcedures"]) == 1


def test_normalize_nocode_keeps_name():
    data = {"主要诊断": "胃窦恶性肿瘤"}  # 字符串形式, 无编码
    out = CaseService._normalize_case_input(data)
    assert out["primaryDiagnosis"]["code"] is None
    assert out["primaryDiagnosis"]["name"] == "胃窦恶性肿瘤"


async def test_create_structured_case(db_session):
    service = CaseService(db_session)
    case = await service.create_case({
        "source_type": "structured",
        "structured_data": {"主要诊断": {"疾病名称": "脑膜炎", "疾病编码": "A01.002+G01*"}},
    })
    assert case.id.startswith("CASE-")
    assert case.primary_diagnosis_code == "A01.002+G01*"
    assert case.status == "parsed"


async def test_import_from_example(db_session):
    service = CaseService(db_session)
    items = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    cases = await service.import_from_example(items)
    assert len(cases) == 3
    assert cases[0].primary_diagnosis_code == "C16.301"


async def test_get_case_not_found_raises(db_session):
    from app.core.exceptions import NotFoundException

    service = CaseService(db_session)
    with pytest.raises(NotFoundException):
        await service.get_case("CASE-NOPE")


async def test_validate_case(db_session):
    service = CaseService(db_session)
    case = await service.create_case({
        "source_type": "structured",
        "structured_data": {"主要诊断": {"疾病名称": "脑膜炎", "疾病编码": "A01.002+G01*"}},
    })
    result = await service.validate_case(case.id)
    assert result["is_valid"] is True

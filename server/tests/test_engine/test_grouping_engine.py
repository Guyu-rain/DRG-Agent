"""入组引擎集成单元测试。参照 plans/phase1_backend.md §2.6。

包含 4 个示例回归用例 (来自 example/drg_example.json)。
"""

import pytest
from app.engine.grouping_engine import GroupingEngine

# 4 个回归用例: (主诊断, 次要诊断列表, 主要手术, 预期 MDC/ADRG/DRG/并发症)
_REGRESSION = [
    ("A01.002+G01*", ["J96.0"], "38.1000x002", "MDCB", "BB1", "BB11", "MCC"),
    ("C16.301", ["K66.002", "Z98.800x108", "I63.801", "K76.807"], "43.7x03",
     "MDCG", "GB2", "GB29", "CC"),
    ("J86.000x013", ["K66.002", "C22.100", "Z98.800x115"], "34.8200x002",
     "MDCE", "EC2", "EC29", "CC"),
    ("K83.105", ["K83.109", "K83.807", "K66.007", "Z43.402"], "51.6303",
     "MDCH", "HC1", "HC15", "NONE"),
]


@pytest.fixture
def engine(rule_index) -> GroupingEngine:
    return GroupingEngine(rule_index)


@pytest.mark.parametrize("primary,secondary,proc,mdc,adrg,drg,cc", _REGRESSION)
def test_regression_cases(engine, primary, secondary, proc, mdc, adrg, drg, cc):
    case = {
        "primaryDiagnosis": {"code": primary, "name": "诊断"},
        "secondaryDiagnoses": [{"code": c, "name": "次诊断"} for c in secondary],
        "primaryProcedure": {"code": proc, "name": "手术"},
    }
    result = engine.group(case)
    assert result["is_grouped"] is True
    assert (result["mdc_code"], result["adrg_code"], result["drg_code"]) == (mdc, adrg, drg)
    assert result["complication"] == cc


def test_course_example_evidence_chain_has_5_steps(engine, course_case):
    result = engine.group(course_case)
    assert len(result["evidence"]) == 5
    assert [e["step"] for e in result["evidence"]] == [1, 2, 3, 4, 5]


def test_course_example_candidate_rules(engine, course_case):
    result = engine.group(course_case)
    hits = [c for c in result["candidate_rules"] if c["hit"]]
    assert len(hits) == 1
    assert hits[0]["drg"] == "BB11"


def test_missing_primary_diagnosis(engine):
    result = engine.group({"primaryDiagnosis": {}})
    assert result["is_grouped"] is False
    assert result["stage"] == "mdc_matching"


def test_unmatched_mdc(engine):
    result = engine.group({"primaryDiagnosis": {"code": "Z99.9", "name": "未知"}})
    assert result["is_grouped"] is False
    assert result["stage"] == "mdc_matching"


def test_mcc_excluded_downgrades_drg(engine):
    # I10 主诊断 -> MDCF 内科 ADRG; 次诊断 I10 被排除 -> NONE
    case = {
        "primaryDiagnosis": {"code": "I10", "name": "原发性高血压"},
        "secondaryDiagnoses": [{"code": "I10", "name": "原发性高血压"}],
    }
    result = engine.group(case)
    assert result["is_grouped"] is True
    assert result["complication"] == "NONE"

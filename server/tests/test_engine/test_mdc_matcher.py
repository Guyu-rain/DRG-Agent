"""MDC 匹配单元测试。参照 plans/phase1_backend.md §2.3。"""

from app.engine.mdc_matcher import match_mdc


def test_match_course_example(rule_index):
    result = match_mdc("A01.002+G01*", rule_index)
    assert result["code"] == "MDCB"


def test_match_c16(rule_index):
    assert match_mdc("C16.301", rule_index)["code"] == "MDCG"


def test_match_unknown_code_returns_none(rule_index):
    result = match_mdc("Z99.9", rule_index)
    assert result["code"] is None
    assert result["reason"]


def test_match_empty_code(rule_index):
    result = match_mdc("", rule_index)
    assert result["code"] is None


def test_prefix_match_works_for_subcodes(rule_index):
    # ICD A01.0 应能命中前缀 A01
    assert match_mdc("A01.0", rule_index)["code"] == "MDCB"


def test_evidence_records_matched_prefix(rule_index):
    result = match_mdc("J86.000x013", rule_index)
    assert result["code"] == "MDCE"
    assert result["matched_prefix"] == "J86"
    assert "J86" in result["evidence"]["matched_rule"]

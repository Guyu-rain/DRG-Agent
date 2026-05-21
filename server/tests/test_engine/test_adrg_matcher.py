"""ADRG 匹配单元测试。参照 plans/phase1_backend.md §2.4。"""

from app.engine.adrg_matcher import match_adrg


def test_match_surgical_adrg(rule_index):
    result = match_adrg("MDCB", "A01.002+G01*", "38.1000x002", rule_index)
    assert result["code"] == "BB1"
    assert result["is_surgical"] is True


def test_match_gb2(rule_index):
    assert match_adrg("MDCG", "C16.301", "43.7x03", rule_index)["code"] == "GB2"


def test_no_procedure_falls_back_to_internal_adrg(rule_index):
    result = match_adrg("MDCB", "A01.002", None, rule_index)
    assert result["code"] == "BS1"
    assert result["is_surgical"] is False


def test_unmatched_surgery_falls_back_to_internal(rule_index):
    result = match_adrg("MDCG", "C16.301", "99.9999", rule_index)
    assert result["code"] == "GS1"


def test_unknown_mdc_returns_none(rule_index):
    result = match_adrg("MDCZ", "X00", "00.00", rule_index)
    assert result["code"] is None
    assert result["reason"]

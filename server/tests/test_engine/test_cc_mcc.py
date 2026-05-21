"""MCC/CC 判定与排除表单元测试。参照 plans/phase1_backend.md §2.5。"""

from app.engine.cc_mcc import check_exclusion, evaluate_cc_mcc


def test_mcc_hit(rule_index):
    result = evaluate_cc_mcc(["J96.0"], "A01.002+G01*", rule_index)
    assert result["level"] == "MCC"
    assert result["excluded_codes"] == []


def test_cc_hit(rule_index):
    result = evaluate_cc_mcc(["K66.002"], "C16.301", rule_index)
    assert result["level"] == "CC"


def test_no_secondary_is_none(rule_index):
    assert evaluate_cc_mcc([], "K83.105", rule_index)["level"] == "NONE"


def test_unknown_secondary_is_none(rule_index):
    result = evaluate_cc_mcc(["K83.109", "K66.007"], "K83.105", rule_index)
    assert result["level"] == "NONE"


def test_mcc_takes_priority_over_cc(rule_index):
    result = evaluate_cc_mcc(["K66.002", "J96.0"], "A01.002", rule_index)
    assert result["level"] == "MCC"


def test_excluded_cc_downgrades_to_none(rule_index):
    # I10 是 CC, 但被主诊断 I10 的排除表排除
    result = evaluate_cc_mcc(["I10"], "I10", rule_index)
    assert result["level"] == "NONE"
    assert result["matched_codes"] == []
    assert result["excluded_codes"]


def test_check_exclusion_direct(rule_index):
    assert check_exclusion("I10", "I10", rule_index) is True
    assert check_exclusion("J96.0", "A01.002+G01*", rule_index) is False

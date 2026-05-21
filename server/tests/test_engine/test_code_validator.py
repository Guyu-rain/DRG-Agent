"""编码校验器单元测试。参照 plans/phase1_backend.md §2.1。"""

from app.engine.code_validator import (
    validate_case_codes,
    validate_icd_cm3_format,
    validate_icd_format,
)


def test_icd_format_course_example():
    assert validate_icd_format("A01.002+G01*") is True


def test_icd_format_simple_code():
    assert validate_icd_format("J96.0") is True


def test_icd_format_only_checks_shape_not_dictionary():
    # 仅做格式校验, 不查词表; ZZZ999 形状合法
    assert validate_icd_format("ZZZ999") is True


def test_icd_format_empty_is_invalid():
    assert validate_icd_format("") is False
    assert validate_icd_format(None) is False


def test_icd_format_rejects_underscore():
    assert validate_icd_format("INVALID_CODE") is False


def test_icd_format_requires_digit():
    assert validate_icd_format("ABC") is False


def test_icd_cm3_format_valid():
    assert validate_icd_cm3_format("38.1000x002") is True
    assert validate_icd_cm3_format("43.7x03") is True


def test_icd_cm3_format_rejects_letter_start():
    assert validate_icd_cm3_format("INVALID") is False


def test_validate_case_codes_all_valid():
    case = {
        "primaryDiagnosis": {"code": "A01.002+G01*", "name": "伤寒性脑膜炎"},
        "secondaryDiagnoses": [{"code": "J96.0", "name": "急性呼吸衰竭"}],
        "primaryProcedure": {"code": "38.1000x002", "name": "手术"},
    }
    result = validate_case_codes(case)
    assert result["is_valid"] is True
    assert result["errors"] == []


def test_validate_case_codes_missing_primary():
    result = validate_case_codes({"primaryDiagnosis": {}})
    assert result["is_valid"] is False
    assert any("主诊断" in e for e in result["errors"])


def test_validate_case_codes_nocode_warns_not_errors():
    case = {"primaryDiagnosis": {"name": "胃窦恶性肿瘤"}}  # 仅名称无编码
    result = validate_case_codes(case)
    assert result["is_valid"] is True  # warning 不阻止流程
    assert any("编码缺失" in w for w in result["warnings"])

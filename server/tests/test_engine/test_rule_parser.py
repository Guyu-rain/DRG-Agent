"""规则解析与索引构建单元测试。参照 plans/phase1_backend.md §2.2。"""

from pathlib import Path

from app.engine.rule_parser import build_rule_index, count_rules, parse_rule_file

_DEMO = Path(__file__).resolve().parents[2] / "data" / "rules" / "demo_rules.json"


def test_parse_demo_rules_succeeds():
    rules = parse_rule_file(_DEMO)
    assert rules["parse_errors"] == []
    assert len(rules["mdc_list"]) >= 1


def test_parse_nonexistent_file_returns_errors_not_raise():
    rules = parse_rule_file("nonexistent_rules.xlsx")
    assert rules["parse_errors"]  # 非空
    assert rules["mdc_list"] == []


def test_parse_unsupported_format():
    rules = parse_rule_file("rules.txt")
    assert any("不支持" in e or "不存在" in e for e in rules["parse_errors"])


def test_count_rules():
    rules = parse_rule_file(_DEMO)
    counts = count_rules(rules)
    assert counts["mdc"] >= 1
    assert counts["adrg"] >= 1
    assert counts["drg"] >= 1


def test_build_index_icd_to_mdc():
    rules = parse_rule_file(_DEMO)
    index = build_rule_index(rules)
    assert index["icd_to_mdc"]["A01"] == "MDCB"
    assert index["icd_to_mdc"]["C16"] == "MDCG"


def test_build_index_has_o1_structures():
    rules = parse_rule_file(_DEMO)
    index = build_rule_index(rules)
    assert isinstance(index["mcc_set"], set)
    assert "J96.0" in index["mcc_set"]
    assert "BB1" in index["adrg_drg_map"]


def test_parse_csv_rules(tmp_path):
    csv_content = (
        "rule_type,code,name,mdc,adrg,cc_level,icd_prefixes,surgery_list,is_surgical,excluded_by\n"
        "mdc,MDCB,神经系统,,,,A01;G00,,,\n"
        "adrg,BB1,神经复合手术,MDCB,,,,38.1000x002,true,\n"
        "drg,BB11,伴严重并发症,,BB1,MCC,,,,\n"
        "mcc,J96.0,急性呼吸衰竭,,,,,,,\n"
        "cc,K66.002,肠粘连,,,,,,,\n"
        "exclusion,I10,,,,,,,,I10\n"
    )
    csv_file = tmp_path / "rules.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    rules = parse_rule_file(csv_file)
    assert rules["parse_errors"] == []
    assert rules["mdc_list"][0]["code"] == "MDCB"
    assert rules["adrg_list"][0]["surgery_list"] == ["38.1000x002"]
    assert rules["drg_list"][0]["cc_level"] == "MCC"
    index = build_rule_index(rules)
    assert index["icd_to_mdc"]["A01"] == "MDCB"


def test_parse_excel_rules(tmp_path):
    from openpyxl import Workbook

    workbook = Workbook()
    mdc_sheet = workbook.active
    mdc_sheet.title = "mdc"
    mdc_sheet.append(["code", "name", "icd_prefixes"])
    mdc_sheet.append(["MDCB", "神经系统", "A01;G00"])
    adrg_sheet = workbook.create_sheet("adrg")
    adrg_sheet.append(["code", "name", "mdc", "surgery_list", "is_surgical"])
    adrg_sheet.append(["BB1", "神经复合手术", "MDCB", "38.1000x002", 1])
    xlsx_file = tmp_path / "rules.xlsx"
    workbook.save(xlsx_file)

    rules = parse_rule_file(xlsx_file)
    assert rules["parse_errors"] == []
    assert rules["mdc_list"][0]["code"] == "MDCB"
    assert rules["adrg_list"][0]["mdc"] == "MDCB"


def test_parse_malformed_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    rules = parse_rule_file(bad)
    assert rules["parse_errors"]

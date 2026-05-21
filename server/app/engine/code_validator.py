"""编码格式校验器 (确定性, 不调用 LLM)。

参照 plans/phase1_backend.md §2.1。仅做格式校验, 不查词表。
"""

from __future__ import annotations

import re

# ICD 诊断编码: 字母开头, 由字母/数字与符号 . / + * 组成, 且至少包含一个数字。
# 例: A01.002+G01*, J96.0, I10
_ICD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9./+*]*$")

# ICD-CM-3 手术编码: 数字开头, 由数字/字母/小数点组成。
# 例: 38.1000x002, 43.7x03, 51.6303
_ICD_CM3_RE = re.compile(r"^[0-9][0-9A-Za-z.]*$")


def validate_icd_format(code: str | None) -> bool:
    """验证 ICD 诊断编码格式。

    Returns:
        True 表示格式合法; False 表示为空或格式非法。
    """
    if not code or not str(code).strip():
        return False
    c = str(code).strip()
    return bool(_ICD_RE.match(c)) and any(ch.isdigit() for ch in c)


def validate_icd_cm3_format(code: str | None) -> bool:
    """验证 ICD-CM-3 手术/操作编码格式。

    Returns:
        True 表示格式合法; False 表示为空或格式非法。
    """
    if not code or not str(code).strip():
        return False
    c = str(code).strip()
    return bool(_ICD_CM3_RE.match(c)) and len(c) >= 2


def validate_case_codes(parsed_case: dict) -> dict:
    """对结构化病历的全部编码进行批量校验。

    Args:
        parsed_case: 形如 {primaryDiagnosis, secondaryDiagnoses, primaryProcedure, otherProcedures}。

    Returns:
        {"is_valid": bool, "errors": [str], "warnings": [str], "results": [dict]}。
        errors 阻止入组; warnings (如缺编码) 不阻止流程。
    """
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict] = []

    primary = parsed_case.get("primaryDiagnosis") or {}
    if not primary or not primary.get("name"):
        errors.append("主诊断缺失")
    elif not primary.get("code"):
        warnings.append(f"主诊断编码缺失，仅有名称: {primary.get('name')}")
        results.append({"field": "primaryDiagnosis.code", "isValid": False, "code": None})
    elif not validate_icd_format(primary["code"]):
        errors.append(f"主诊断编码格式错误: {primary['code']}")
        results.append({"field": "primaryDiagnosis.code", "isValid": False, "code": primary["code"]})
    else:
        results.append({"field": "primaryDiagnosis.code", "isValid": True, "code": primary["code"]})

    for idx, diag in enumerate(parsed_case.get("secondaryDiagnoses") or []):
        code = diag.get("code")
        field = f"secondaryDiagnoses[{idx}].code"
        if code and not validate_icd_format(code):
            errors.append(f"次要诊断编码格式错误: {code}")
            results.append({"field": field, "isValid": False, "code": code})
        elif not code and diag.get("name"):
            warnings.append(f"次要诊断仅名称无编码: {diag.get('name')}")
            results.append({"field": field, "isValid": False, "code": None})
        elif code:
            results.append({"field": field, "isValid": True, "code": code})

    procedures: list[tuple[str, dict]] = []
    if parsed_case.get("primaryProcedure"):
        procedures.append(("primaryProcedure.code", parsed_case["primaryProcedure"]))
    for idx, proc in enumerate(parsed_case.get("otherProcedures") or []):
        procedures.append((f"otherProcedures[{idx}].code", proc))

    for field, proc in procedures:
        code = proc.get("code")
        if code and not validate_icd_cm3_format(code):
            errors.append(f"手术编码格式错误: {code}")
            results.append({"field": field, "isValid": False, "code": code})
        elif not code and proc.get("name"):
            warnings.append(f"手术仅名称无编码: {proc.get('name')}")
            results.append({"field": field, "isValid": False, "code": None})
        elif code:
            results.append({"field": field, "isValid": True, "code": code})

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }

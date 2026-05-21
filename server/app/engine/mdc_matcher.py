"""MDC 匹配 (主诊断 ICD 编码 -> MDC)。

参照 plans/phase1_backend.md §2.3。确定性前缀匹配, 不调用 LLM。
"""

from __future__ import annotations


def _normalize(code: str | None) -> str:
    return str(code).strip() if code else ""


def match_mdc(primary_diag_code: str | None, rule_index: dict) -> dict:
    """根据主诊断 ICD 编码匹配 MDC。

    采用最长前缀匹配: 在 ``rule_index['icd_to_mdc']`` 中找到所有为该编码前缀的
    条目, 取最长者命中。

    Returns:
        成功: {"code", "name", "matched_prefix", "evidence"}
        失败: {"code": None, "reason", "candidates": [...]}
    """
    code = _normalize(primary_diag_code)
    icd_to_mdc: dict[str, str] = rule_index.get("icd_to_mdc", {})
    mdc_names: dict[str, str] = rule_index.get("mdc_names", {})

    if not code:
        return {"code": None, "reason": "主诊断编码缺失，无法匹配 MDC", "candidates": []}

    matched_prefixes = [prefix for prefix in icd_to_mdc if prefix and code.startswith(prefix)]
    if not matched_prefixes:
        return {
            "code": None,
            "reason": f"主诊断 {code} 无法匹配任何 MDC",
            "candidates": [],
        }

    best_prefix = max(matched_prefixes, key=len)
    mdc_code = icd_to_mdc[best_prefix]
    mdc_name = mdc_names.get(mdc_code, mdc_code)
    return {
        "code": mdc_code,
        "name": mdc_name,
        "matched_prefix": best_prefix,
        "evidence": {
            "type": "mdc_match",
            "matched_code": code,
            "matched_rule": f"{mdc_code} ICD前缀: {best_prefix}",
            "description": f"主诊断 {code} 命中 ICD 前缀 {best_prefix}，进入 {mdc_code}（{mdc_name}）",
        },
    }

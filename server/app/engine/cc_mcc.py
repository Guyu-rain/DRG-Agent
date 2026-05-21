"""MCC/CC 并发症判定与排除表检查 (确定性, 不调用 LLM)。

参照 plans/phase1_backend.md §2.5。
"""

from __future__ import annotations


def check_exclusion(diag_code: str, primary_diag_code: str | None, rule_index: dict) -> bool:
    """检查某个次要诊断是否被主诊断的排除表排除。

    当主诊断编码以排除表中任一前缀开头时, 视为被排除。
    """
    if not diag_code or not primary_diag_code:
        return False
    excluded_by = rule_index.get("exclusion_map", {}).get(diag_code, [])
    primary = str(primary_diag_code).strip()
    return any(prefix and primary.startswith(prefix) for prefix in excluded_by)


def evaluate_cc_mcc(
    secondary_diag_codes: list[str],
    primary_diag_code: str | None,
    rule_index: dict,
) -> dict:
    """评估并发症等级 (MCC > CC > NONE)。

    步骤: 先在 MCC/CC 列表中匹配次要诊断, 再逐一做排除表检查;
    被排除的编码不参与等级判定。

    Returns:
        {"level", "matched_codes": [{code, level}], "excluded_codes": [{code, reason}], "warnings": [str]}
    """
    mcc_set: set = rule_index.get("mcc_set", set())
    cc_set: set = rule_index.get("cc_set", set())
    mcc_names: dict = rule_index.get("mcc_names", {})
    cc_names: dict = rule_index.get("cc_names", {})

    matched: list[dict] = []
    excluded: list[dict] = []
    warnings: list[str] = []

    for code in secondary_diag_codes:
        if not code:
            continue
        if code in mcc_set:
            level = "MCC"
            name = mcc_names.get(code, code)
        elif code in cc_set:
            level = "CC"
            name = cc_names.get(code, code)
        else:
            warnings.append(f"次要诊断 {code} 不在 MCC/CC 列表中")
            continue

        if check_exclusion(code, primary_diag_code, rule_index):
            excluded.append({
                "code": code,
                "level": level,
                "reason": f"{code}（{name}）被主诊断 {primary_diag_code} 的排除表排除",
            })
        else:
            matched.append({"code": code, "level": level, "name": name})

    has_mcc = any(item["level"] == "MCC" for item in matched)
    has_cc = any(item["level"] == "CC" for item in matched)
    level = "MCC" if has_mcc else ("CC" if has_cc else "NONE")

    return {
        "level": level,
        "matched_codes": matched,
        "excluded_codes": excluded,
        "warnings": warnings,
    }

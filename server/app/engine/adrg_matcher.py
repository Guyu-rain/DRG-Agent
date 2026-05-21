"""ADRG 匹配 (MDC + 主要手术 -> ADRG)。

参照 plans/phase1_backend.md §2.4。优先匹配手术类 ADRG, 无手术编码或未命中
时回退到内科类 ADRG。
"""

from __future__ import annotations


def _normalize(code: str | None) -> str:
    return str(code).strip() if code else ""


def match_adrg(
    mdc_code: str,
    primary_diag_code: str | None,
    primary_proc_code: str | None,
    rule_index: dict,
) -> dict:
    """在指定 MDC 下匹配 ADRG。

    Returns:
        成功: {"code", "name", "is_surgical", "evidence"}
        失败: {"code": None, "reason"}
    """
    adrg_names: dict[str, str] = rule_index.get("adrg_names", {})
    adrg_by_mdc: dict[str, list[str]] = rule_index.get("adrg_by_mdc", {})
    surgery_adrg: dict[str, list[str]] = rule_index.get("surgery_adrg", {})
    internal_adrg: dict[str, str] = rule_index.get("internal_adrg_by_mdc", {})
    adrg_diagnosis: dict[str, list[str]] = rule_index.get("adrg_diagnosis", {})

    mdc_adrgs = set(adrg_by_mdc.get(mdc_code, []))
    if not mdc_adrgs:
        return {"code": None, "reason": f"MDC={mdc_code} 下没有任何 ADRG 规则"}

    proc = _normalize(primary_proc_code)
    # 1) 手术类匹配: 主要手术编码命中 ADRG 手术列表
    if proc:
        for adrg_code in surgery_adrg.get(proc, []):
            if adrg_code in mdc_adrgs:
                name = adrg_names.get(adrg_code, adrg_code)
                return {
                    "code": adrg_code,
                    "name": name,
                    "is_surgical": True,
                    "evidence": {
                        "type": "adrg_match",
                        "matched_code": proc,
                        "matched_rule": f"{adrg_code} 手术列表: {proc}",
                        "description": f"主要手术 {proc} 在 {mdc_code} 下命中 {adrg_code}（{name}）",
                    },
                }

    # 2) 内科类回退: 无手术编码或手术未命中时, 匹配内科 ADRG
    diag = _normalize(primary_diag_code)
    internal_code = internal_adrg.get(mdc_code)
    if internal_code and internal_code in mdc_adrgs:
        name = adrg_names.get(internal_code, internal_code)
        prefixes = adrg_diagnosis.get(internal_code, [])
        diag_hit = next((p for p in prefixes if diag and diag.startswith(p)), None)
        reason = (
            f"主诊断 {diag} 命中诊断前缀 {diag_hit}" if diag_hit else "无手术编码，按内科组处理"
        )
        return {
            "code": internal_code,
            "name": name,
            "is_surgical": False,
            "evidence": {
                "type": "adrg_match",
                "matched_code": diag or None,
                "matched_rule": f"{internal_code} 内科组",
                "description": f"{reason}，进入内科 ADRG {internal_code}（{name}）",
            },
        }

    if proc:
        return {"code": None, "reason": f"主要手术 {proc} 在 MDC={mdc_code} 下未命中任何 ADRG"}
    return {"code": None, "reason": f"MDC={mdc_code} 下无可用的内科 ADRG"}

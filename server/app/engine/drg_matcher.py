"""DRG 最终分组 (ADRG + 并发症等级 -> DRG)。

参照 plans/phase1_backend.md §2.6 step 5。
"""

from __future__ import annotations

_LEVEL_LABEL = {"MCC": "伴严重合并症或并发症", "CC": "伴合并症或并发症", "NONE": "不伴合并症或并发症"}


def match_drg(adrg_code: str, cc_level: str, rule_index: dict) -> dict:
    """在指定 ADRG 下根据并发症等级匹配最终 DRG。

    Returns:
        成功: {"code", "name", "cc_level", "candidates": [{adrg, drg, name, reason, hit}]}
        失败: {"code": None, "reason"}
    """
    entries: list[dict] = rule_index.get("adrg_drg_map", {}).get(adrg_code, [])
    if not entries:
        return {"code": None, "reason": f"ADRG={adrg_code} 下没有 DRG 规则"}

    cc_level = (cc_level or "NONE").upper()
    chosen = next((e for e in entries if e["cc_level"] == cc_level), None)
    if chosen is None:
        # 回退: 优先 NONE 档, 否则取第一条
        chosen = next((e for e in entries if e["cc_level"] == "NONE"), entries[0])

    candidates: list[dict] = []
    for entry in entries:
        hit = entry["drg_code"] == chosen["drg_code"]
        if hit:
            reason = f"命中（并发症等级={cc_level}）"
        else:
            reason = f"未命中（需并发症等级={entry['cc_level']}，实际={cc_level}）"
        candidates.append({
            "adrg": adrg_code,
            "drg": entry["drg_code"],
            "name": entry["name"],
            "reason": reason,
            "hit": hit,
        })

    return {
        "code": chosen["drg_code"],
        "name": chosen["name"],
        "cc_level": cc_level,
        "candidates": candidates,
        "evidence": {
            "type": "drg_final",
            "matched_rule": f"{adrg_code}→{chosen['drg_code']}：并发症等级={cc_level}",
            "description": (
                f"{adrg_code} 在并发症等级 {cc_level}（{_LEVEL_LABEL.get(cc_level, cc_level)}）下"
                f"最终进入 {chosen['drg_code']}（{chosen['name']}）"
            ),
        },
    }

"""DRG 入组引擎 —— 整合 MDC→ADRG→CC/MCC→DRG 的完整确定性流程。

参照 plans/phase1_backend.md §2.6 与 plans/02_architecture.md §3。
本模块为纯 Python 算法, 不调用 LLM, 结果可复现、可审计。
"""

from __future__ import annotations

from app.engine.adrg_matcher import match_adrg
from app.engine.cc_mcc import evaluate_cc_mcc
from app.engine.code_validator import validate_case_codes
from app.engine.drg_matcher import match_drg
from app.engine.mdc_matcher import match_mdc


class GroupingEngine:
    """DRG 入组引擎。使用规则索引执行三重匹配。"""

    def __init__(self, rule_index: dict) -> None:
        self.rule_index = rule_index

    def group(self, parsed_case: dict) -> dict:
        """执行完整的 MDC→ADRG→DRG 入组。

        Args:
            parsed_case: 标准化病历 {primaryDiagnosis, secondaryDiagnoses, primaryProcedure, ...}

        Returns:
            入组结果字典 (见 plans/03_api_interfaces.md §4.2)。
        """
        primary = parsed_case.get("primaryDiagnosis") or {}
        primary_code = primary.get("code")
        primary_proc = (parsed_case.get("primaryProcedure") or {}).get("code")
        secondary = [
            d.get("code") for d in (parsed_case.get("secondaryDiagnoses") or []) if d.get("code")
        ]

        validation = validate_case_codes(parsed_case)
        warnings: list[str] = list(validation["warnings"])

        # Step 1: MDC 匹配 -----------------------------------------------------
        mdc = match_mdc(primary_code, self.rule_index)
        if not mdc.get("code"):
            return self._ungrouped("mdc_matching", mdc.get("reason", "无法匹配 MDC"), warnings=warnings)

        # Step 2: ADRG 匹配 ----------------------------------------------------
        adrg = match_adrg(mdc["code"], primary_code, primary_proc, self.rule_index)
        if not adrg.get("code"):
            return self._ungrouped(
                "adrg_matching",
                adrg.get("reason", "无法匹配 ADRG"),
                mdc=mdc,
                warnings=warnings,
            )

        # Step 3: MCC/CC 判定 --------------------------------------------------
        cc = evaluate_cc_mcc(secondary, primary_code, self.rule_index)
        warnings.extend(cc["warnings"])

        # Step 4: DRG 分组 -----------------------------------------------------
        drg = match_drg(adrg["code"], cc["level"], self.rule_index)
        if not drg.get("code"):
            return self._ungrouped(
                "drg_matching",
                drg.get("reason", "无法匹配 DRG"),
                mdc=mdc,
                adrg=adrg,
                warnings=warnings,
            )

        # Step 5: 证据链构建 ---------------------------------------------------
        evidence = self._build_evidence(mdc, adrg, cc, drg, secondary)

        return {
            "is_grouped": True,
            "mdc_code": mdc["code"],
            "mdc_name": mdc["name"],
            "adrg_code": adrg["code"],
            "adrg_name": adrg["name"],
            "drg_code": drg["code"],
            "drg_name": drg["name"],
            "complication": cc["level"],
            "evidence": evidence,
            "candidate_rules": drg["candidates"],
            "warnings": warnings,
            "ungrouped_reason": None,
            "stage": "completed",
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ungrouped(
        stage: str,
        reason: str,
        mdc: dict | None = None,
        adrg: dict | None = None,
        warnings: list[str] | None = None,
    ) -> dict:
        return {
            "is_grouped": False,
            "stage": stage,
            "ungrouped_reason": reason,
            "mdc_code": mdc["code"] if mdc else None,
            "mdc_name": mdc["name"] if mdc else None,
            "adrg_code": adrg["code"] if adrg else None,
            "adrg_name": adrg["name"] if adrg else None,
            "drg_code": None,
            "drg_name": None,
            "complication": None,
            "evidence": [],
            "candidate_rules": [],
            "warnings": warnings or [],
        }

    @staticmethod
    def _build_evidence(mdc: dict, adrg: dict, cc: dict, drg: dict, secondary: list[str]) -> list[dict]:
        """构建 5 步证据链 (参照 plans/03_api_interfaces.md §4.2)。"""
        ev_mdc = mdc["evidence"]
        ev_adrg = adrg["evidence"]
        ev_drg = drg["evidence"]

        matched_cc = "、".join(f"{m['code']}（{m['name']}）" for m in cc["matched_codes"]) or "无"
        step3_desc = f"次要诊断 {matched_cc} 判定为并发症等级 {cc['level']}"

        excluded_by: list[str] = []
        for item in cc["excluded_codes"]:
            excluded_by.append(item["code"])
        if cc["excluded_codes"]:
            step4_desc = "；".join(item["reason"] for item in cc["excluded_codes"])
            excluded = True
        else:
            step4_desc = "命中的次要诊断均未被主诊断的排除表排除"
            excluded = False

        return [
            {
                "step": 1,
                "type": "mdc_match",
                "description": ev_mdc["description"],
                "matchedCode": ev_mdc["matched_code"],
                "matchedRule": ev_mdc["matched_rule"],
            },
            {
                "step": 2,
                "type": "adrg_match",
                "description": ev_adrg["description"],
                "matchedCode": ev_adrg["matched_code"],
                "matchedRule": ev_adrg["matched_rule"],
            },
            {
                "step": 3,
                "type": "cc_mcc_evaluation",
                "description": step3_desc,
                "matchedCode": [m["code"] for m in cc["matched_codes"]],
                "ccLevel": cc["level"],
            },
            {
                "step": 4,
                "type": "exclusion_check",
                "description": step4_desc,
                "excludedBy": excluded_by,
                "excluded": excluded,
            },
            {
                "step": 5,
                "type": "drg_final",
                "description": ev_drg["description"],
                "matchedRule": ev_drg["matched_rule"],
            },
        ]


def build_grouping_engine(parsed_rules: dict) -> GroupingEngine:
    """便捷工厂: 从解析后的规则构建带索引的入组引擎。"""
    from app.engine.rule_parser import build_rule_index

    return GroupingEngine(build_rule_index(parsed_rules))

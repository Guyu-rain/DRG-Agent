"""
Phase 5: Assemble complete rules.json from all phases.
Combines ADRG definitions, MCC/CC lists, exclusion groups, and derives:
- ICD prefix → MDC mapping (from medical ADRG diagnosis codes)
- DRG codes (from ADRG + CC level convention)
- MDC name mapping

Output: server/data/rules/drg_2.0_full.json
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
RULES_DIR = PROJECT_ROOT / "server" / "data" / "rules"
RULES_DIR.mkdir(parents=True, exist_ok=True)


def load_json(name):
    path = OUTPUT_DIR / name
    if not path.exists():
        print(f"ERROR: {name} not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def derive_icd_to_mdc(adrg_codes):
    """
    Derive ICD-10 prefix -> MDC mapping from medical ADRG diagnosis codes.
    For each medical ADRG, collect unique 3-char ICD prefixes from its codes,
    and map them to the ADRG's MDC.
    """
    icd_to_mdc = {}
    mdc_prefixes = defaultdict(set)

    for adrg in adrg_codes:
        mdc = adrg.get("mdc", "")
        if not mdc or mdc == "UNKNOWN":
            continue
        if adrg.get("type") != "diagnosis":
            continue

        for code_entry in adrg.get("codes", []):
            code = code_entry.get("code", "")
            if not code:
                continue
            # Extract first 3 chars as prefix (e.g., "A01" from "A01.002+G01*")
            prefix_match = re.match(r"^([A-Z]\d{2})", code)
            if prefix_match:
                prefix = prefix_match.group(1)
                mdc_prefixes[mdc].add(prefix)

    # Convert to icd_to_mdc: prefix -> mdc_code
    for mdc, prefixes in mdc_prefixes.items():
        for prefix in prefixes:
            if prefix not in icd_to_mdc:
                icd_to_mdc[prefix] = mdc
            # If conflict, keep the first (most specific) assignment

    return icd_to_mdc, mdc_prefixes


def derive_drg_codes(adrg_codes):
    """
    Derive DRG codes from ADRG + CC level convention.
    
    Naming convention (DRG 2.0):
    - Each surgical ADRG produces 3 DRGs: +1=MCC, +3=CC, +5=NONE (or +9=CC for some)
    - Medical ADRGs produce 1 DRG: +9=NONE
    
    We use a lookup table for known exceptions and default patterns.
    """
    # CC level suffix mapping (default patterns)
    # For most ADRGs: 1=MCC, 3=CC, 5=NONE
    # Some ADRGs ending in 2 use: 1=MCC, 9=CC, 5=NONE
    drg_list = []

    for adrg in adrg_codes:
        code = adrg["code"]
        name = adrg.get("name", "")
        mdc = adrg.get("mdc", "")
        adrg_type = adrg.get("type", "")

        if adrg_type == "surgery":
            # Surgical ADRG: 3 DRG codes
            # Determine CC suffix pattern
            last_digit = code[-1] if code[-1].isdigit() else code[-2]
            if last_digit in ("2", "4", "6", "8"):
                cc_suffix = "9"  # ADRGs ending in 2/4/6/8 use 9 for CC
            else:
                cc_suffix = "3"  # Others use 3 for CC

            drg_list.extend([
                {"code": f"{code}1", "name": f"{name}，伴严重合并症或并发症",
                 "adrg": code, "cc_level": "MCC"},
                {"code": f"{code}{cc_suffix}", "name": f"{name}，伴合并症或并发症",
                 "adrg": code, "cc_level": "CC"},
                {"code": f"{code}5", "name": f"{name}，不伴合并症或并发症",
                 "adrg": code, "cc_level": "NONE"},
            ])
        else:
            # Medical ADRG: 1 DRG code (NONE)
            drg_list.append({
                "code": f"{code}9",
                "name": f"{name}",
                "adrg": code,
                "cc_level": "NONE",
            })

    return drg_list


def build_mdc_list(adrg_codes, icd_to_mdc, mdc_prefixes):
    """Build MDC list with names and ICD prefixes."""
    # MDC name mapping from standard DRG 2.0
    mdc_names = {
        "MDCA": "先期分组",
        "MDCB": "神经系统疾病及功能障碍",
        "MDCC": "眼疾病及功能障碍",
        "MDCD": "头颈、耳、鼻、口、咽疾病及功能障碍",
        "MDCE": "呼吸系统疾病及功能障碍",
        "MDCF": "循环系统疾病及功能障碍",
        "MDCG": "消化系统疾病及功能障碍",
        "MDCH": "肝、胆、胰疾病及功能障碍",
        "MDCI": "肌肉骨骼系统疾病及功能障碍",
        "MDCJ": "皮肤、皮下组织及乳腺疾病及功能障碍",
        "MDCK": "内分泌、营养、代谢疾病及功能障碍",
        "MDCL": "肾脏及泌尿系统疾病及功能障碍",
        "MDCM": "男性生殖系统疾病及功能障碍",
        "MDCN": "女性生殖系统疾病及功能障碍",
        "MDCO": "妊娠、分娩及产褥期",
        "MDCP": "新生儿及其他围产期疾病",
        "MDCQ": "血液、免疫疾病及功能障碍",
        "MDCR": "骨髓增生性疾病及功能障碍，低分化肿瘤",
        "MDCS": "感染及寄生虫病（全身性或非特指部位）",
        "MDCT": "精神疾病及功能障碍",
        "MDCU": "酒精/药物使用及其所致障碍",
        "MDCV": "创伤、中毒及药物毒性效应",
        "MDCW": "烧伤",
        "MDCX": "影响健康因素及其他就医情况",
        "MDCY": "HIV感染疾病及相关操作",
        "MDCZ": "多发严重创伤",
    }

    mdc_list = []
    all_mdcs = set()

    # Collect all MDCs from ADRGs
    for adrg in adrg_codes:
        mdc = adrg.get("mdc", "")
        if mdc and mdc != "UNKNOWN":
            all_mdcs.add(mdc)

    for mdc_code in sorted(all_mdcs):
        name = mdc_names.get(mdc_code, mdc_code)
        prefixes = sorted(mdc_prefixes.get(mdc_code, set()))
        mdc_list.append({
            "code": mdc_code,
            "name": name,
            "icd_prefixes": prefixes,
        })

    return mdc_list


def main():
    print("=" * 60)
    print("Phase 5: Assembling rules.json")
    print("=" * 60)

    # Load all phase data
    print("\n[1/6] Loading phase data...")
    phase2 = load_json("phase2_adrg_codes.json")
    phase3 = load_json("phase3_mcc_cc.json")
    phase4 = load_json("phase4_exclusion_groups.json")

    print(f"  ADRGs: {len(phase2)}")
    print(f"  MCC: {len(phase3['mcc_list'])}")
    print(f"  CC: {len(phase3['cc_list'])}")
    print(f"  Exclusion codes: {len(phase4['code_to_group'])}")

    # Derive ICD prefix → MDC mapping
    print("\n[2/6] Deriving ICD→MDC prefix mapping...")
    icd_to_mdc, mdc_prefixes = derive_icd_to_mdc(phase2)
    print(f"  Unique ICD prefixes: {len(icd_to_mdc)}")
    print(f"  MDCs covered: {len(mdc_prefixes)}")

    # Build MDC list
    print("\n[3/6] Building MDC list...")
    mdc_list = build_mdc_list(phase2, icd_to_mdc, mdc_prefixes)
    print(f"  MDCs: {len(mdc_list)}")

    # Build ADRG list
    print("\n[4/6] Building ADRG list...")
    adrg_list = []
    for adrg in phase2:
        entry = {
            "code": adrg["code"],
            "name": adrg.get("name", ""),
            "mdc": adrg.get("mdc", ""),
            "is_surgical": adrg.get("type") == "surgery",
        }
        codes = adrg.get("codes", [])
        if adrg.get("type") == "surgery":
            entry["surgery_list"] = [c["code"] for c in codes]
            entry["diagnosis_list"] = []
        else:
            entry["surgery_list"] = []
            entry["diagnosis_list"] = [c["code"] for c in codes]
        adrg_list.append(entry)
    print(f"  ADRGs: {len(adrg_list)}")

    # Derive DRG codes
    print("\n[5/6] Deriving DRG codes...")
    drg_list = derive_drg_codes(phase2)
    print(f"  DRGs: {len(drg_list)}")

    # Build MCC/CC lists
    mcc_list = [{"code": e["code"], "name": e["name"], "level": "MCC"}
                for e in phase3["mcc_list"]]
    cc_list = [{"code": e["code"], "name": e["name"], "level": "CC"}
               for e in phase3["cc_list"]]

    # Build exclusion table: group by exclusion_group, use ICD prefixes
    # This is much more compact than listing all full codes
    code_to_group = phase4["code_to_group"]
    group_to_codes = phase4["group_to_codes"]

    # Pre-compute: for each group, extract unique ICD prefixes
    group_prefixes = {}
    for group_str, codes in group_to_codes.items():
        prefixes = set()
        for c in codes:
            m = re.match(r"^([A-Z]\d{2})", c)
            if m:
                prefixes.add(m.group(1))
        group_prefixes[group_str] = sorted(prefixes)

    exclusion_table = []
    for entry in phase3["mcc_list"] + phase3["cc_list"]:
        mcc_cc_code = entry["code"]
        excl_group = entry.get("exclusion_table")
        if excl_group is not None:
            excl_key = str(excl_group)
            prefixes = group_prefixes.get(excl_key, [])
            exclusion_table.append({
                "diag_code": mcc_cc_code,
                "excluded_by": prefixes,
            })

    # Assemble final rules
    rules = {
        "_meta": {
            "version_name": "DRG 2.0 完整规则 (自动提取)",
            "description": "从《按病组（DRG）付费分组方案（2.0版）》PDF自动提取",
            "format": "drg-agent-rule-json-v1",
            "extraction_info": {
                "total_adrg": len(adrg_list),
                "total_drg": len(drg_list),
                "total_mcc": len(mcc_list),
                "total_cc": len(cc_list),
                "total_exclusion_groups": len(group_prefixes),
                "total_icd_prefixes": len(icd_to_mdc),
                "mdc_count": len(mdc_list),
            },
        },
        "mdc_list": mdc_list,
        "adrg_list": adrg_list,
        "drg_list": drg_list,
        "mcc_list": mcc_list,
        "cc_list": cc_list,
        "exclusion_table": exclusion_table,
    }

    # Save
    output_path = RULES_DIR / "drg_2.0_full.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    file_size = output_path.stat().st_size
    print(f"\n[6/6] Saved to: {output_path}")
    print(f"  File size: {file_size / 1024 / 1024:.1f} MB")

    # Quality Verification
    print(f"\n{'=' * 60}")
    print("QUALITY VERIFICATION")
    print(f"{'=' * 60}")

    info = rules["_meta"]["extraction_info"]
    print(f"  MDCs:              {info['mdc_count']}")
    print(f"  ADRGs:             {info['total_adrg']}")
    print(f"  DRGs:              {info['total_drg']}")
    print(f"  MCC codes:         {info['total_mcc']}")
    print(f"  CC codes:          {info['total_cc']}")
    print(f"  Exclusion groups:  {info['total_exclusion_groups']}")
    print(f"  ICD prefixes:      {info['total_icd_prefixes']}")
    print(f"  File size:         {file_size / 1024 / 1024:.1f} MB")

    # Verify demo rules compatibility
    demo_adrgs = {"BB1", "BS1", "GB2", "HC1", "EC2"}
    found = {a["code"] for a in adrg_list}
    print(f"\n  Demo ADRGs present:")
    for code in sorted(demo_adrgs):
        status = "✓" if code in found else "✗"
        print(f"    {status} {code}")

    # Verify known MCC/CC
    mcc_codes = {e["code"] for e in mcc_list}
    cc_codes = {e["code"] for e in cc_list}
    for code in ["J96.000", "I50.000", "K66.002"]:
        if code in mcc_codes:
            print(f"    ✓ {code} → MCC")
        elif code in cc_codes:
            print(f"    ✓ {code} → CC")
        else:
            print(f"    ✗ {code} → NOT FOUND")

    # Engine compatibility check
    print(f"\n  Engine compatibility:")
    print(f"    mdc_list format OK:     {'icd_prefixes' in str(mdc_list[:1])}")
    print(f"    adrg_list format OK:    {'is_surgical' in str(adrg_list[:1])}")
    print(f"    drg_list format OK:     {'cc_level' in str(drg_list[:1])}")
    print(f"    mcc_list format OK:    {len(mcc_list) > 0}")
    print(f"    cc_list format OK:     {len(cc_list) > 0}")
    print(f"    exclusion_table OK:    {len(exclusion_table) > 0}")


if __name__ == "__main__":
    main()

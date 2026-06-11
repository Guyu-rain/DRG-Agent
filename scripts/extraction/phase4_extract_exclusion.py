"""
Phase 4: Extract exclusion group mapping from DRG 2.0 PDF.
Pages 1316-1737 contain all codes with their "排除内容" (exclusion group) references.

Builds a lookup: ICD_code -> exclusion_group_number
Used by the engine to check if a primary diagnosis excludes an MCC/CC code.
(MCC codes from Phase 3 also included for completeness.)

Output: scripts/extraction/output/phase4_exclusion_groups.json
"""

import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = PROJECT_ROOT / "file" / "DRG.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_WORKERS = 2


def parse_exclusion_page(pdf, page_num):
    """
    Parse one page of exclusion data.
    Returns list of {code, name, exclusion_group} dicts.
    """
    text = pdf.pages[page_num].extract_text()
    if not text:
        return []

    entries = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "疾病编码" in line or "疾病名称" in line:
            continue
        if line.startswith("表6-") and len(line) < 30:
            continue
        if re.match(r"^\d+$", line):
            continue
        if "合并症" in line and len(line) < 30:
            continue

        # Pattern: code + name + 表6-3-N
        m = re.match(r"^([A-Z]\d{2}[\.\dx]\S*)\s+(.+?)\s+表6-3-(\d+)", line)
        if not m:
            # Try: code + name (no table ref)
            m2 = re.match(r"^([A-Z]\d{2}[\.\dx]\S*)\s+(.+)", line)
            if m2:
                code = m2.group(1)
                name = m2.group(2).strip().rstrip("，。、；")
                entries.append({"code": code, "name": name, "exclusion_group": None})
            continue

        code = m.group(1)
        name = m.group(2).strip().rstrip("，。、；")
        group = int(m.group(3))
        entries.append({"code": code, "name": name, "exclusion_group": group})

    return entries


def process_page_range(args):
    """Worker for parallel extraction."""
    pdf_path, start_page, end_page = args
    pdf = pdfplumber.open(pdf_path)
    results = []
    for pg in range(start_page, end_page):
        results.extend(parse_exclusion_page(pdf, pg))
    pdf.close()
    return results


def main():
    print("=" * 60)
    print("Phase 4: Extracting Exclusion Group Mapping")
    print("=" * 60)

    # Load Phase 3 for MCC codes' exclusion groups
    phase3_path = OUTPUT_DIR / "phase3_mcc_cc.json"
    if not phase3_path.exists():
        print("ERROR: Phase 3 data not found.")
        sys.exit(1)

    with open(phase3_path, "r", encoding="utf-8") as f:
        phase3 = json.load(f)

    # Build initial group map from MCC codes
    group_map = {}
    for e in phase3["mcc_list"]:
        if e.get("exclusion_table") is not None:
            group_map[e["code"]] = e["exclusion_table"]
    for e in phase3["cc_list"]:
        if e.get("exclusion_table") is not None:
            group_map[e["code"]] = e["exclusion_table"]

    print(f"\n[1/4] Initial group map from MCC/CC: {len(group_map)} entries")

    # Extract all diagnoses from pages 1316-1737
    # This includes CC codes AND diagnoses from exclusion tables
    total_pages = 1737 - 1316 + 1
    print(f"[2/4] Extracting from pages 1316-1737 ({total_pages} pages)")

    # Split into batches for parallel processing
    all_pages = list(range(1315, 1737))  # 0-indexed
    batch_size = max(1, len(all_pages) // (N_WORKERS * 4))
    batches = [all_pages[i:i + batch_size] for i in range(0, len(all_pages), batch_size)]
    worker_args = [(str(PDF_PATH), batch[0], batch[-1] + 1) for batch in batches]

    with Pool(N_WORKERS) as pool:
        all_results = pool.map(process_page_range, worker_args)

    # Merge into group map
    total_new = 0
    for batch in all_results:
        for entry in batch:
            if entry["code"] not in group_map and entry["exclusion_group"] is not None:
                group_map[entry["code"]] = entry["exclusion_group"]
                total_new += 1

    print(f"[3/4] Total exclusion group map: {len(group_map)} entries ({total_new} new)")

    # Build reverse lookup: group -> list of codes
    group_to_codes = {}
    for code, group in group_map.items():
        if group is not None:
            group_to_codes.setdefault(group, []).append(code)

    print(f"  Unique exclusion groups: {len(group_to_codes)}")
    for g in sorted(group_to_codes.keys())[:10]:
        print(f"    Group {g}: {len(group_to_codes[g])} codes")

    # Save
    output = {
        "code_to_group": {k: v for k, v in sorted(group_map.items())},
        "group_to_codes": {str(k): v for k, v in sorted(group_to_codes.items())},
        "total_codes": len(group_map),
        "total_groups": len(group_to_codes),
    }

    output_path = OUTPUT_DIR / "phase4_exclusion_groups.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[4/4] Output saved to: {output_path}")

    # Quality Verification
    print(f"\n{'=' * 60}")
    print("QUALITY VERIFICATION")
    print(f"{'=' * 60}")

    # Verify known exclusion patterns from demo
    # J96.000 (MCC, group 104): should NOT be excluded by A01.002 (check)
    # I10 (primary): should exclude itself
    j96_group = group_map.get("J96.000")
    a01_group = group_map.get("A01.002")
    i10_group = group_map.get("I10.x00") or group_map.get("I10")

    print(f"  J96.000 group: {j96_group}")
    print(f"  A01.002 group: {a01_group}")
    print(f"  I10 group: {i10_group}")

    if j96_group and a01_group:
        if j96_group == a01_group:
            print(f"  ✗ A01.002 would INCORRECTLY exclude J96.000")
        else:
            print(f"  ✓ A01.002 would NOT exclude J96.000 (groups differ: {j96_group} != {a01_group})")

    # Demo case verification: course example
    # Primary: A01.002+G01*, Secondary (MCC): J96.0
    # Expected: J96.0 should NOT be excluded (different groups)
    a01g_code = "A01.002+G01*"
    if a01g_code not in group_map:
        print(f"  ⚠ {a01g_code} not in group map, checking A01.002")
    else:
        print(f"  A01.002+G01* group: {group_map[a01g_code]}")

    print(f"\n  Exclusion engine logic: primary_group == mcc_group → EXCLUDED")
    print(f"  Total mapped codes: {len(group_map)}")


if __name__ == "__main__":
    main()

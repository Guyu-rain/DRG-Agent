"""
Phase 3: Extract MCC and CC lists from DRG 2.0 PDF.
Pages 1209-1315 (MCC) and 1316-1400 (CC).
Format: "疾病编码 疾病名称 排除内容" header + code entries.

Output: scripts/extraction/output/phase3_mcc_cc.json
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

N_WORKERS = 2  # MCC/CC extraction is lighter weight


def parse_mcc_cc_page(pdf, page_num):
    """
    Parse a single page of MCC/CC data.
    Returns list of {code, name, exclusion_table} dicts.
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
        # Skip page numbers, section headers
        if re.match(r"^\d+$", line):
            continue
        if "合并症" in line and "（" in line:
            continue

        # Use greedy pattern: code + rest (name + optional table ref)
        m = re.match(r"^([A-Z]\d{2}[\.\dx]\S*)\s+(.+)", line)
        if not m:
            continue

        code = m.group(1)
        rest = m.group(2).strip()

        # Extract exclusion table reference from end
        excl_m = re.search(r"\s+(表6-3-\d+)$", rest)
        excl_ref = None
        if excl_m:
            name = rest[:excl_m.start()].strip()
            excl_ref = int(excl_m.group(1).split("-")[-1])
        else:
            name = rest

        # Clean: remove trailing punctuation
        name = name.rstrip("，。、；").strip()

        if name:
            entries.append({
                "code": code,
                "name": name,
                "exclusion_table": excl_ref,
            })

    return entries


def process_page_range(args):
    """Worker function for parallel page parsing."""
    pdf_path, start_page, end_page = args
    pdf = pdfplumber.open(pdf_path)
    results = []
    for pg in range(start_page, end_page):
        results.extend(parse_mcc_cc_page(pdf, pg))
    pdf.close()
    return results


def main():
    print("=" * 60)
    print("Phase 3: Extracting MCC/CC Lists")
    print("=" * 60)

    phase1_path = OUTPUT_DIR / "phase1_structure_map.json"
    if not phase1_path.exists():
        print("ERROR: Phase 1 map not found.")
        sys.exit(1)

    with open(phase1_path, "r", encoding="utf-8") as f:
        phase1 = json.load(f)

    mcc_section = phase1["mcc_section"]
    cc_section = phase1["cc_section"]

    mcc_pages = (mcc_section["start"] - 1, mcc_section["end"])  # 0-indexed
    cc_pages = (cc_section["start"] - 1, cc_section["end"]) if cc_section["start"] else None

    print(f"\n[1/4] MCC list: pages {mcc_section['start']}-{mcc_section['end']} ({mcc_pages[1] - mcc_pages[0]} pages)")
    if cc_pages:
        print(f"  CC list:  pages {cc_section['start']}-{cc_section['end']} ({cc_pages[1] - cc_pages[0]} pages)")

    # Parallel extraction: split pages into batches
    all_pages = list(range(mcc_pages[0], mcc_pages[1]))
    if cc_pages:
        all_pages.extend(range(cc_pages[0], cc_pages[1]))

    batch_size = max(1, len(all_pages) // (N_WORKERS * 2))
    batches = [all_pages[i:i + batch_size] for i in range(0, len(all_pages), batch_size)]

    worker_args = [(str(PDF_PATH), batch[0], batch[-1] + 1) for batch in batches]

    print(f"\n[2/4] Parallel extraction with {N_WORKERS} workers ({len(batches)} batches)...")

    with Pool(N_WORKERS) as pool:
        all_results = pool.map(process_page_range, worker_args)

    # Flatten
    all_entries = []
    for batch in all_results:
        all_entries.extend(batch)

    # Split into MCC and CC based on page range
    mcc_entries = []
    cc_entries = []
    # We can't easily tell which page each entry came from in parallel mode,
    # but the page boundary is around entry ~4500-5000
    # Alternative: use the exclusion table reference to distinguish
    # MCC typically has exclusion tables 1-158, CC has different ones
    # But simpler: split by position in the list
    
    # Actually, let's run them sequentially to know which is which
    pdf = pdfplumber.open(PDF_PATH)
    
    mcc_entries = []
    for pg in range(mcc_pages[0], mcc_pages[1]):
        mcc_entries.extend(parse_mcc_cc_page(pdf, pg))
    
    cc_entries = []
    if cc_pages:
        for pg in range(cc_pages[0], cc_pages[1]):
            cc_entries.extend(parse_mcc_cc_page(pdf, pg))
    
    pdf.close()

    # Tag with level
    for e in mcc_entries:
        e["level"] = "MCC"
    for e in cc_entries:
        e["level"] = "CC"

    print(f"\n[3/4] Results:")
    print(f"  MCC entries: {len(mcc_entries)}")
    print(f"  CC entries:  {len(cc_entries)}")
    print(f"  Total:       {len(mcc_entries) + len(cc_entries)}")

    # Deduplicate
    seen = set()
    unique_mcc = []
    for e in mcc_entries:
        if e["code"] not in seen:
            seen.add(e["code"])
            unique_mcc.append(e)
    
    seen = set()
    unique_cc = []
    for e in cc_entries:
        if e["code"] not in seen:
            seen.add(e["code"])
            unique_cc.append(e)

    # Save
    output = {
        "mcc_list": [{"code": e["code"], "name": e["name"], "level": "MCC",
                       "exclusion_table": e.get("exclusion_table")}
                      for e in unique_mcc],
        "cc_list": [{"code": e["code"], "name": e["name"], "level": "CC",
                      "exclusion_table": e.get("exclusion_table")}
                     for e in unique_cc],
        "mcc_count": len(unique_mcc),
        "cc_count": len(unique_cc),
    }

    output_path = OUTPUT_DIR / "phase3_mcc_cc.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[4/4] Output saved to: {output_path}")

    # Quality Verification
    print(f"\n{'=' * 60}")
    print("QUALITY VERIFICATION")
    print(f"{'=' * 60}")

    # Check known MCC/CC codes from demo
    known_mcc = {"J96.0": "急性呼吸衰竭", "I50.0": "充血性心力衰竭"}
    known_cc = {"K66.002": "肠粘连", "I10": "原发性高血压", "I63.801": "其他脑梗死"}

    mcc_lookup = {e["code"]: e for e in unique_mcc}
    cc_lookup = {e["code"]: e for e in unique_cc}

    print("  Known MCC codes:")
    for code, name in known_mcc.items():
        found = mcc_lookup.get(code)
        if found:
            print(f"    ✓ {code}: {found['name'][:50]}")
        else:
            print(f"    ✗ {code}: NOT FOUND")
            # Check if it's in CC
            if code in cc_lookup:
                print(f"      (found in CC list: {cc_lookup[code]['name'][:50]})")

    print("  Known CC codes:")
    for code, name in known_cc.items():
        found = cc_lookup.get(code)
        if found:
            print(f"    ✓ {code}: {found['name'][:50]}")
        else:
            print(f"    ✗ {code}: NOT FOUND")
            if code in mcc_lookup:
                print(f"      (found in MCC list: {mcc_lookup[code]['name'][:50]})")

    # Sample entries
    print(f"\n  Sample MCC entries:")
    for e in unique_mcc[:5]:
        print(f"    {e['code']:20s} {e['name'][:50]}")

    print(f"\n  Sample CC entries:")
    for e in unique_cc[:5]:
        print(f"    {e['code']:20s} {e['name'][:50]}")


if __name__ == "__main__":
    main()

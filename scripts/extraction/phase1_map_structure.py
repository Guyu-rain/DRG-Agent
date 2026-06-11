"""
Phase 1: Map DRG 2.0 PDF structure (Revised).
Uses "包含以下" markers + backwards ADRG header lookup for robust detection.
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

import pdfplumber

PDF_PATH = Path(__file__).resolve().parents[2] / "file" / "DRG.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ADRG code pattern: 2 uppercase letters + 1-2 digits + optional single letter
ADRG_CODE_RE = re.compile(r"\b([A-Z]{2}\d{1,2}[A-Z]?)\b")
ICD_CODE_RE = re.compile(r"^[A-Z]\d{2}[\.\dx]")  # ICD-10 pattern
SECTION_MARKER_RE = re.compile(
    r"(包含以下主要手术|包含以下主要诊断|同时包含以下手术|同时包含以下诊断)"
)

# Known MDC codes
MDC_CODES = [f"MDC{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]


def get_full_text(pdf, start_page, end_page):
    """Extract concatenated text from a page range."""
    texts = []
    for pg in range(start_page, end_page):
        t = pdf.pages[pg].extract_text()
        if t:
            texts.append(t)
    return "\n".join(texts)


def find_adrg_definitions_v2(pdf):
    """
    Scan pages 65-1112 for ADRG definitions.
    Strategy: find "包含以下" markers, then search backwards for ADRG code.
    """
    adrg_defs = []
    # Pre-scan to find all section marker positions
    markers = []  # List of (page, char_index, marker_type)

    for pg in range(64, 1112):
        text = pdf.pages[pg].extract_text()
        if not text:
            continue
        for m in SECTION_MARKER_RE.finditer(text):
            marker_type = "surgery" if "手术" in m.group(1) else "diagnosis"
            markers.append((pg, m.start(), m.end(), marker_type, text))

    print(f"  Found {len(markers)} section markers")

    # For each marker, find the nearest preceding ADRG code
    for pg, start, end, mtype, text in markers:
        # Look backwards from the marker position
        before = text[:start]

        # Find all ADRG codes before this marker
        adrg_matches = list(ADRG_CODE_RE.finditer(before))
        if not adrg_matches:
            # Check previous page
            if pg > 64:
                prev_text = pdf.pages[pg - 1].extract_text() or ""
                adrg_matches = list(ADRG_CODE_RE.finditer(prev_text))
                if adrg_matches:
                    text = prev_text

        if adrg_matches:
            last_match = adrg_matches[-1]
            code = last_match.group(1)
            if code in MDC_CODES:
                continue  # Skip MDC codes

            # Get the ADRG name (text after the code until next code or line end)
            after_code = text[last_match.end():]
            # Extract name as Chinese characters after the code
            name_match = re.match(r"\s*([\u4e00-\u9fff\uff00-\uffef、/（）()\w]+)", after_code)
            name = name_match.group(1).strip() if name_match else ""

            # Check for duplicates
            if not any(a["code"] == code for a in adrg_defs):
                adrg_defs.append(
                    {
                        "code": code,
                        "name": name[:80],
                        "page": pg + 1,
                        "type": mtype,
                    }
                )

    return adrg_defs


def find_mdc_section_boundaries(pdf):
    """
    Find where each MDC's ADRG definitions start and end.
    Uses the ADRG list's MDC headers on pages ~39-42 or scans for MDC headers
    in the ADRG detail section.
    """
    # First try to find MDC headers in ADRG detail section (pages 65-1112)
    mdc_boundaries = []
    current_mdc = None
    mdc_header_re = re.compile(r"MDC([A-Z])\s+(\S.*)$")

    for pg in range(64, 1112):
        text = pdf.pages[pg].extract_text()
        if not text:
            continue

        lines = text.strip().split("\n")
        for line in lines[:3]:  # Only check first 3 lines
            line_s = line.strip()
            m = mdc_header_re.match(line_s)
            if m:
                code = f"MDC{m.group(1)}"
                name = m.group(2)
                # If we find "先期分组" or other qualifiers in the name, extract just the MDC part
                if current_mdc:
                    current_mdc["end_page"] = pg + 1
                current_mdc = {
                    "code": code,
                    "name": name[:80],
                    "start_page": pg + 1,
                    "end_page": None,
                }
                mdc_boundaries.append(current_mdc)
                break

    if current_mdc:
        current_mdc["end_page"] = 1112

    return mdc_boundaries


def assign_mdc_to_adrgs(adrg_defs, mdc_boundaries):
    """Assign each ADRG to MDC using naming convention (first letter → MDC)."""
    mdc_map = {
        "A": "MDCA", "B": "MDCB", "C": "MDCC", "D": "MDCD",
        "E": "MDCE", "F": "MDCF", "G": "MDCG", "H": "MDCH",
        "I": "MDCI", "J": "MDCJ", "K": "MDCK", "L": "MDCL",
        "M": "MDCM", "N": "MDCN", "O": "MDCO", "P": "MDCP",
        "Q": "MDCQ", "R": "MDCR", "S": "MDCS", "T": "MDCT",
        "U": "MDCU", "V": "MDCV", "W": "MDCW", "X": "MDCX",
        "Y": "MDCY", "Z": "MDCZ",
    }
    for adrg in adrg_defs:
        # Primary: use naming convention (standard DRG 2.0)
        first_letter = adrg["code"][0]
        adrg["mdc"] = mdc_map.get(first_letter, "UNKNOWN")


def find_mcc_cc_boundary(pdf):
    """Find the MCC and CC list page ranges."""
    # Scan pages 1208-1400 for the CC header
    mcc_start = 1209
    mcc_end = 1400
    cc_start = None

    for pg in range(1208, 1400):
        text = pdf.pages[pg].extract_text()
        if not text:
            continue
        for line in text.strip().split("\n")[:5]:
            if "合并症或并发症（CC）" in line or "表6-1-2" in line:
                cc_start = pg + 1
                break
        if cc_start:
            mcc_end = cc_start - 1
            break

    if not cc_start:
        # Fallback: estimate split point (MCC and CC share similar format)
        cc_start = 1350

    return {"mcc_start": mcc_start, "mcc_end": mcc_end, "cc_start": cc_start, "cc_end": 1400}


def find_adrg_dir_list(pdf):
    """Extract all ADRG codes and names from the ADRG directory (pages 39-43)."""
    all_adrg = []
    # Pages 39-43 have the format "ADRG编码 ADRG名称" header followed by "CODE NAME" entries
    for pg in range(38, 50):
        text = pdf.pages[pg].extract_text()
        if not text:
            continue
        for line in text.strip().split("\n"):
            line = line.strip()
            # Skip header lines
            if "ADRG编码" in line or "ADRG名称" in line:
                continue
            # Format: "CODE NAME" where CODE is [A-Z]{2}\d+[A-Z]?
            m = re.match(r"^([A-Z]{2}\d{1,2}[A-Z]?)\s(.+)$", line)
            if m and not m.group(1).startswith("MDC"):
                code = m.group(1)
                name = m.group(2).strip()
                all_adrg.append({"code": code, "name": name})
    return all_adrg


def main():
    print("=" * 60)
    print("Phase 1 (v2): Mapping DRG 2.0 PDF Structure")
    print("=" * 60)

    print(f"\n[1/6] Opening PDF: {PDF_PATH}")
    pdf = pdfplumber.open(PDF_PATH)
    total_pages = len(pdf.pages)
    print(f"  Total pages: {total_pages}")

    # 1. Extract ADRG directory listing
    print("\n[2/6] Extracting ADRG directory listing (pages 39-64)...")
    adrg_dir = find_adrg_dir_list(pdf)
    print(f"  Found {len(adrg_dir)} ADRGs in directory listing")

    # 2. Find MDC section boundaries
    print("\n[3/6] Finding MDC section boundaries...")
    mdc_boundaries = find_mdc_section_boundaries(pdf)
    print(f"  Found {len(mdc_boundaries)} MDC sections")

    # 3. Find ADRG detail definitions
    print("\n[4/6] Finding ADRG detail definitions...")
    adrg_details = find_adrg_definitions_v2(pdf)
    assign_mdc_to_adrgs(adrg_details, mdc_boundaries)

    surgical = [a for a in adrg_details if a["type"] == "surgery"]
    medical = [a for a in adrg_details if a["type"] == "diagnosis"]
    print(f"  Found {len(adrg_details)} ADRG detail definitions")
    print(f"    Surgical: {len(surgical)}")
    print(f"    Medical:  {len(medical)}")

    # Cross-reference with directory
    detail_codes = {a["code"] for a in adrg_details}
    dir_codes = {a["code"] for a in adrg_dir}
    only_dir = dir_codes - detail_codes
    only_detail = detail_codes - dir_codes
    if only_dir:
        print(f"  ⚠ {len(only_dir)} ADRGs in directory but NOT in details: {list(only_dir)[:10]}")
    if only_detail:
        print(f"  ⚠ {len(only_detail)} ADRGs in details but NOT in directory: {list(only_detail)[:10]}")

    # 4. MCC/CC boundary
    print("\n[5/6] Finding MCC/CC boundaries...")
    mcc_cc = find_mcc_cc_boundary(pdf)
    print(f"  MCC: pages {mcc_cc['mcc_start']}-{mcc_cc['mcc_end']} ({mcc_cc['mcc_end'] - mcc_cc['mcc_start'] + 1} pages)")
    if mcc_cc["cc_start"]:
        print(f"  CC:  pages {mcc_cc['cc_start']}-{mcc_cc['cc_end']} ({mcc_cc['cc_end'] - mcc_cc['cc_start'] + 1} pages)")

    # 6. Exclusion tables
    print("\n[6/6] Finding exclusion table boundaries...")
    print(f"  Exclusion tables: pages 1401-1737 (337 pages)")

    # Compile all data into ADRG directory lookup
    dir_lookup = {a["code"]: a["name"] for a in adrg_dir}
    for adrg in adrg_details:
        if adrg["code"] in dir_lookup:
            adrg["dir_name"] = dir_lookup[adrg["code"]]

    # Build output
    output = {
        "pdf_path": str(PDF_PATH),
        "total_pages": total_pages,
        "adrg_section": {"start": 65, "end": 1112},
        "mdc_boundaries": mdc_boundaries,
        "adrg_directory_count": len(adrg_dir),
        "adrg_detail_count": len(adrg_details),
        "adrg_definitions": adrg_details,
        "mcc_section": {"start": mcc_cc["mcc_start"], "end": mcc_cc["mcc_end"]},
        "cc_section": {"start": mcc_cc["cc_start"], "end": mcc_cc["cc_end"]},
        "exclusion_section": {"start": 1401, "end": 1737},
    }

    output_path = OUTPUT_DIR / "phase1_structure_map.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # === Quality report ===
    print(f"\n{'=' * 60}")
    print("QUALITY REPORT")
    print(f"{'=' * 60}")
    print(f"  MDC sections found:  {len(mdc_boundaries)} (expected 26)")
    print(f"  ADRG in directory:   {len(adrg_dir)} (expected ~409)")
    print(f"  ADRG detail defs:    {len(adrg_details)} (expected ~409)")
    print(f"    - Surgical type:    {len(surgical)}")
    print(f"    - Medical type:     {len(medical)}")

    # Cross-reference quality
    if len(adrg_dir) >= 300:
        print(f"  ✓ ADRG directory count looks reasonable (>=300)")
    else:
        print(f"  ✗ ADRG directory count low ({len(adrg_dir)}), check parsing")

    if len(adrg_details) >= 350:
        print(f"  ✓ ADRG detail count reasonable (>=350)")
    else:
        print(f"  ✗ ADRG detail count low ({len(adrg_details)}), check parsing")

    print(f"\n  Map saved to: {output_path}")

    pdf.close()


if __name__ == "__main__":
    main()

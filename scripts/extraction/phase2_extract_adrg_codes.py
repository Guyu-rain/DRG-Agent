"""
Phase 2 (v2): Extract ADRG surgery/diagnosis code lists using between-headers approach.
Handles multiple codes per line and line-wrapping.

Strategy:
  For each ADRG, collect ALL codes between its header position and the NEXT ADRG header.
  Surgical ADRGs -> ICD-9-CM-3 surgery codes (start with digit)
  Medical ADRGs -> ICD-10 diagnosis codes (start with letter)

Output: scripts/extraction/output/phase2_adrg_codes.json
"""

import json
import re
import sys
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = PROJECT_ROOT / "file" / "DRG.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ICD code start patterns
ICD10_START = re.compile(r"^[A-Z]\d{2}[\.\dx]")     # ICD-10 diagnosis
ICD9_START = re.compile(r"^\d{2}\.\d")              # ICD-9-CM-3 surgery
ADRG_CODE_RE = re.compile(r"\b([A-Z]{2}\d{1,2}[A-Z]?)\b")
MDC_CODES = {f"MDC{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}

N_WORKERS = 4


def extract_all_codes_from_text(text, code_type):
    """
    Extract all codes of a given type from raw text.
    Handles multiple codes per line and line-wrapping.
    
    Args:
        text: raw text to scan
        code_type: 'surgery' or 'diagnosis'
    
    Returns:
        list of {code, name} dicts
    """
    codes = []
    # Tokenize: split by whitespace but track positions
    tokens = re.split(r'(\s+)', text)
    
    i = 0
    while i < len(tokens):
        token = tokens[i].strip()
        if not token:
            i += 1
            continue
        
        # Check if this token starts a code
        is_code = False
        if code_type == "surgery":
            is_code = bool(ICD9_START.match(token))
        else:
            is_code = bool(ICD10_START.match(token))
        
        if is_code:
            code = token
            # Collect name: all tokens until next code or end
            name_parts = []
            i += 1
            while i < len(tokens):
                next_token = tokens[i].strip()
                if not next_token:
                    i += 1
                    continue
                # Stop if next token is another code
                if code_type == "surgery":
                    if ICD9_START.match(next_token):
                        break
                else:
                    if ICD10_START.match(next_token):
                        break
                # Also stop if next token is an ADRG header
                if ADRG_CODE_RE.fullmatch(next_token) and next_token not in MDC_CODES:
                    break
                name_parts.append(next_token)
                i += 1
            
            name = " ".join(name_parts).strip()
            # Clean: remove stray punctuation at end
            name = name.rstrip("，。；、")
            if name:
                codes.append({"code": code, "name": name})
        else:
            i += 1
    
    return codes


def find_adrg_code_positions(pdf, adrg_page, adrg_code):
    """
    Find the character position where an ADRG's codes start.
    Looks for the ADRG header on its page, then finds the start of codes.
    """
    for pg in range(adrg_page, min(adrg_page + 3, len(pdf.pages))):
        text = pdf.pages[pg].extract_text()
        if not text:
            continue
        
        # Find the ADRG header exactly
        idx = text.find(adrg_code)
        if idx < 0:
            continue
        
        # The code position starts after the ADRG header name
        # Find where the header ends (after the Chinese name)
        after_header = text[idx + len(adrg_code):]
        # Skip whitespace and Chinese characters (ADRG name)
        m = re.match(r"\s*([\u4e00-\u9fff\uff00-\uffef、/（）()，。\w\s-]+?)(?=\s*\d{2}\.|\s*[A-Z]\d{2}|\s*[A-Z]{2}\d|\s*$)", after_header)
        if m:
            header_end = idx + len(adrg_code) + m.end()
            return pg, header_end
        
        # Fallback: just start after the ADRG code
        return pg, idx + len(adrg_code)
    
    return None, None


def process_page_range(args):
    """
    Worker function for parallel ADRG code extraction.
    Uses between-headers approach.
    """
    adrg_batch, all_adrg_pages, pdf_path = args
    
    pdf = pdfplumber.open(pdf_path)
    results = []
    
    for adrg in adrg_batch:
        adrg_code = adrg["code"]
        adrg_page = adrg["page"] - 1
        adrg_type = adrg["type"]
        
        # Find all ADRG positions sorted by page+char
        # We need the next ADRG after this one to know where to stop
        sorted_adrgs = sorted(all_adrg_pages, key=lambda x: (x[1], x[2]))
        
        # Find current ADRG position
        current_pos = None
        next_pos = None
        for i, (code, pg, pos) in enumerate(sorted_adrgs):
            if code == adrg_code:
                current_pos = (pg, pos)
                if i + 1 < len(sorted_adrgs):
                    next_pos = (sorted_adrgs[i + 1][1], sorted_adrgs[i + 1][2])
                break
        
        if current_pos is None:
            results.append({
                "code": adrg_code, "name": adrg.get("name", ""),
                "mdc": adrg.get("mdc", ""), "type": adrg_type,
                "codes": [], "warning": "position not found"
            })
            continue
        
        # Collect text from current to next ADRG
        start_pg, start_pos = current_pos
        codes = []
        
        if next_pos:
            end_pg, end_pos = next_pos
        else:
            end_pg = min(start_pg + 10, len(pdf.pages))
            end_pos = 999999
        
        for pg in range(start_pg, min(end_pg + 1, len(pdf.pages))):
            text = pdf.pages[pg].extract_text()
            if not text:
                continue
            
            if pg == start_pg:
                text = text[start_pos:]
            if pg == end_pg and next_pos:
                text = text[:end_pos]
            
            codes.extend(extract_all_codes_from_text(text, adrg_type))
        
        # Deduplicate by code
        seen = set()
        unique_codes = []
        for c in codes:
            if c["code"] not in seen:
                seen.add(c["code"])
                unique_codes.append(c)
        
        results.append({
            "code": adrg_code,
            "name": adrg.get("name", ""),
            "mdc": adrg.get("mdc", ""),
            "type": adrg_type,
            "page": adrg["page"],
            "codes": unique_codes,
            "code_count": len(unique_codes),
        })
    
    pdf.close()
    return results


def find_all_adrg_positions(pdf_path, adrg_defs):
    """Find the precise page+char position of each ADRG header in the PDF."""
    pdf = pdfplumber.open(pdf_path)
    positions = []
    
    for adrg in adrg_defs:
        adrg_page = adrg["page"] - 1
        adrg_code = adrg["code"]
        
        for pg in range(adrg_page, min(adrg_page + 3, len(pdf.pages))):
            text = pdf.pages[pg].extract_text()
            if not text:
                continue
            idx = text.find(adrg_code)
            if idx >= 0:
                # Verify it's actually an ADRG header (followed by Chinese name)
                after = text[idx + len(adrg_code):idx + len(adrg_code) + 5]
                if re.search(r"[\u4e00-\u9fff]", after):
                    positions.append((adrg_code, pg, idx))
                    break
    
    pdf.close()
    return positions


def main():
    print("=" * 60)
    print("Phase 2 (v2): Extracting ADRG Code Lists")
    print("  Method: Between-headers with multi-code parsing")
    print("=" * 60)
    
    phase1_path = OUTPUT_DIR / "phase1_structure_map.json"
    if not phase1_path.exists():
        print("ERROR: Phase 1 map not found.")
        sys.exit(1)
    
    with open(phase1_path, "r", encoding="utf-8") as f:
        phase1 = json.load(f)
    
    adrg_defs = phase1["adrg_definitions"]
    print(f"\n[1/5] Loaded {len(adrg_defs)} ADRG definitions")
    
    # Pre-scan to find all ADRG positions (needed for "next ADRG" boundaries)
    print(f"\n[2/5] Pre-scanning ADRG positions in PDF...")
    all_positions = find_all_adrg_positions(str(PDF_PATH), adrg_defs)
    print(f"  Found positions for {len(all_positions)}/{len(adrg_defs)} ADRGs")
    
    # Split batches for parallel processing
    batch_size = max(1, len(adrg_defs) // N_WORKERS)
    batches = [adrg_defs[i:i + batch_size] for i in range(0, len(adrg_defs), batch_size)]
    
    worker_args = [(batch, all_positions, str(PDF_PATH)) for batch in batches]
    
    print(f"\n[3/5] Parallel extraction with {N_WORKERS} workers ({len(batches)} batches)...")
    
    with Pool(N_WORKERS) as pool:
        all_results = pool.map(process_page_range, worker_args)
    
    flat_results = []
    for batch in all_results:
        flat_results.extend(batch)
    flat_results.sort(key=lambda x: x["code"])
    
    # Statistics
    total_codes = sum(r.get("code_count", 0) for r in flat_results)
    surgical = [r for r in flat_results if r["type"] == "surgery"]
    medical = [r for r in flat_results if r["type"] == "diagnosis"]
    
    print(f"\n[4/5] Statistics:")
    print(f"  ADRGs processed:  {len(flat_results)}")
    print(f"  Surgical ADRGs:   {len(surgical)}")
    print(f"  Medical ADRGs:    {len(medical)}")
    print(f"  Total codes:      {total_codes}")
    if surgical:
        surg_codes = sum(r.get("code_count", 0) for r in surgical)
        print(f"  Avg surg codes:   {surg_codes / len(surgical):.1f}")
    if medical:
        med_codes = sum(r.get("code_count", 0) for r in medical)
        print(f"  Avg med codes:    {med_codes / len(medical):.1f}")
    
    # Quality checks
    empty = [r for r in flat_results if r.get("code_count", 0) == 0]
    if empty:
        print(f"\n  ⚠ {len(empty)} ADRGs have 0 codes: {[e['code'] for e in empty[:10]]}")
    
    # Save
    output_path = OUTPUT_DIR / "phase2_adrg_codes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flat_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[5/5] Output saved to: {output_path}")
    
    # === Quality Verification ===
    print(f"\n{'=' * 60}")
    print("QUALITY VERIFICATION")
    print(f"{'=' * 60}")
    
    key_adrgs = {
        "BB1": {"type": "surgery", "min_codes": 10, "expected": "38.1000x002"},
        "BS1": {"type": "diagnosis", "min_codes": 10, "expected": "E03.500"},
        "GB2": {"type": "surgery", "min_codes": 5, "expected": "43.7x03"},
        "HC1": {"type": "surgery", "min_codes": 10, "expected": "51.6303"},
        "EC2": {"type": "surgery", "min_codes": 5, "expected": "34.8200x002"},
    }
    
    all_ok = True
    for code, expected in key_adrgs.items():
        found = [r for r in flat_results if r["code"] == code]
        if not found:
            print(f"  ✗ {code}: NOT FOUND")
            all_ok = False
        else:
            r = found[0]
            codes = r.get("codes", [])
            code_list = [c["code"] for c in codes]
            has_expected = expected["expected"] in code_list
            count = r.get("code_count", len(codes))
            status = "✓" if has_expected and count >= expected["min_codes"] else "✗"
            print(f"  {status} {code}: {count} codes, "
                  f"includes {expected['expected']}={has_expected}, "
                  f"sample: {code_list[:3]}")
            if not has_expected or count < expected["min_codes"]:
                all_ok = False
    
    if all_ok:
        print(f"\n  ✓ All key ADRGs pass verification")
    else:
        print(f"\n  ⚠ Some ADRGs need attention")


if __name__ == "__main__":
    main()

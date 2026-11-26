#!/usr/bin/env python3
"""
extract_thesis_meta.py
-----------------------
Extract title, advisor, keywords, abstract from Abstract PDFs
and update docs/thesis/<YEAR>/index.json entries automatically.

Usage (run on Windows):
  venv\Scripts\python.exe scripts\extract_thesis_meta.py
  venv\Scripts\python.exe scripts\extract_thesis_meta.py --year 2566
  venv\Scripts\python.exe scripts\extract_thesis_meta.py --force   (overwrite existing)
  venv\Scripts\python.exe scripts\extract_thesis_meta.py --dry-run  (preview only)
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber --break-system-packages")
    sys.exit(1)

THESIS_BASE = Path("docs/thesis")

# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path, max_pages: int = 5) -> str:
    """Extract text from first N pages, joined with form-feed separator."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages[:max_pages]:
                txt = page.extract_text()
                if txt:
                    pages.append(txt.strip())
            return "\f".join(pages)
    except Exception as e:
        print(f"  [ERR] Cannot read {pdf_path.name}: {e}")
        return ""


def clean_thai(text: str) -> str:
    """Clean up Thai text: collapse internal double-spaces but preserve single spaces."""
    if not text:
        return ""
    # pdfplumber sometimes inserts a space in the middle of Thai words (font ligature issue)
    # Remove zero-width spaces, collapse multiple whitespace runs to single space
    text = text.replace("​", "").replace("﻿", "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def grab_until_next_label(text: str, start: int, end_patterns: list[str]) -> str:
    """From position `start` in text, grab content until one of end_patterns appears."""
    segment = text[start:]
    earliest = len(segment)
    for pat in end_patterns:
        m = re.search(pat, segment)
        if m and m.start() < earliest:
            earliest = m.start()
    return segment[:earliest].strip()


# ---------------------------------------------------------------------------
# Single-PDF parser
# ---------------------------------------------------------------------------

def parse_abstract_pdf(pdf_path: Path) -> dict:
    """
    Returns dict with keys: title, title_en, advisor, advisor_en,
    keywords, keywords_en, abstract, abstract_en
    All values are strings (may be empty on parse failure).
    """
    full_text = extract_text_from_pdf(pdf_path, max_pages=6)
    if not full_text:
        return {}

    result = {}
    pages = full_text.split("\f")

    # -----------------------------------------------------------------------
    # Thai section: usually page 0 (sometimes page 1 if page 0 is cover)
    # -----------------------------------------------------------------------
    for page_idx in range(min(3, len(pages))):
        thai_page = pages[page_idx]
        if "บทคัดย่อ" in thai_page or "ชื่อเรื่อง" in thai_page:
            # Title
            m = re.search(r"ชื่อเรื่อง\s+(.+)", thai_page)
            if m:
                result["title"] = clean_thai(m.group(1))

            # Author
            m = re.search(r"ผู้(?:ศึกษาวิจัย|วิจัย|เขียน)\s+(.+)", thai_page)
            if m:
                result["author"] = clean_thai(m.group(1))

            # Advisor  (อาจารย์ที่ปรึกษา  หรือ  ที่ปรึกษา)
            m = re.search(r"(?:อาจารย์ที่ปรึกษา|ที่ปรึกษา(?:วิทยานิพนธ์)?)\s+(.+)", thai_page)
            if m:
                raw = m.group(1)
                # Strip degree prefixes: ผศ. / รศ. / ศ. / ดร.
                result["advisor"] = clean_thai(raw)

            # Keywords (คำสำคัญ or ค าส าคัญ with OCR spaces)
            m = re.search(r"ค\s*[าำ]\s*ส\s*[าำ]\s*คัญ\s+(.+?)(?=\n(?:บทคัดย่อ|$))", thai_page, re.DOTALL)
            if not m:
                m = re.search(r"คำสำคัญ\s+(.+?)(?=\n(?:บทคัดย่อ|$))", thai_page, re.DOTALL)
            if m:
                kw = clean_thai(m.group(1).replace("\n", " "))
                result["keywords"] = kw

            # Abstract: everything after บทคัดย่อ in this page and next page(s)
            m = re.search(r"บทคัดย่อ\s*\n(.+)", thai_page, re.DOTALL)
            if m:
                abstract_parts = [m.group(1).strip()]
                # Collect from subsequent Thai pages (until English section starts)
                for np in range(page_idx + 1, min(page_idx + 4, len(pages))):
                    next_page = pages[np]
                    if re.search(r"^Title\s|^ABSTRACT", next_page, re.MULTILINE):
                        break
                    abstract_parts.append(next_page)
                result["abstract"] = clean_thai(" ".join(abstract_parts))
            break

    # -----------------------------------------------------------------------
    # English section: scan for page containing "ABSTRACT" or "Title "
    # -----------------------------------------------------------------------
    for page_idx in range(len(pages)):
        eng_page = pages[page_idx]
        if not re.search(r"^(Title|ABSTRACT)", eng_page, re.MULTILINE | re.IGNORECASE):
            continue

        # English title
        m = re.search(r"^Title\s+(.+?)(?=\n(?:Author|Advisor|Academic))", eng_page,
                      re.MULTILINE | re.DOTALL)
        if not m:
            m = re.search(r"^Title\s+(.+)", eng_page, re.MULTILINE)
        if m:
            result["title_en"] = re.sub(r"\s+", " ", m.group(1)).strip()

        # English advisor
        m = re.search(r"^Advisor\s+(.+?)(?=\n(?:Academic|Keywords|ABSTRACT|Abstract))",
                      eng_page, re.MULTILINE | re.DOTALL)
        if not m:
            m = re.search(r"^Advisor\s+(.+)", eng_page, re.MULTILINE)
        if m:
            result["advisor_en"] = re.sub(r"\s+", " ", m.group(1)).strip()

        # English keywords
        m = re.search(r"^Keywords?\s+(.+?)(?=\nABSTRACT|\nAbstract)", eng_page,
                      re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if not m:
            m = re.search(r"^Keywords?\s+(.+)", eng_page, re.MULTILINE | re.IGNORECASE)
        if m:
            result["keywords_en"] = re.sub(r"\s+", " ", m.group(1)).strip()

        # English abstract
        m = re.search(r"(?:^ABSTRACT|^Abstract)\s*\n(.+)", eng_page,
                      re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if m:
            abstract_en_parts = [m.group(1).strip()]
            for np in range(page_idx + 1, min(page_idx + 4, len(pages))):
                abstract_en_parts.append(pages[np])
            result["abstract_en"] = re.sub(r"\s+", " ", " ".join(abstract_en_parts)).strip()

        break

    return result


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def process_year(year: int, force: bool, dry_run: bool) -> dict:
    index_path = THESIS_BASE / str(year) / "index.json"
    if not index_path.exists():
        return {"year": year, "skipped": 0, "updated": 0, "failed": 0}

    with open(index_path, encoding="utf-8") as f:
        idx_data = json.load(f)

    entries = idx_data.get("entries", [])
    stats = {"year": year, "total": len(entries), "updated": 0, "skipped": 0,
             "no_pdf": 0, "failed": 0}

    for entry in entries:
        # Skip only if ALL text fields are already filled (unless --force)
        text_fields = ("title", "title_en", "advisor", "keywords", "abstract", "abstract_en")
        all_filled = all(bool(entry.get(k, "").strip()) for k in text_fields)
        if all_filled and not force:
            stats["skipped"] += 1
            continue

        # Find PDF to read
        pdf_rel = entry.get("abstract_pdf") or entry.get("fullpaper_pdf")
        if not pdf_rel:
            stats["no_pdf"] += 1
            continue

        pdf_path = THESIS_BASE / pdf_rel
        if not pdf_path.exists():
            print(f"  [MISSING] {pdf_rel}")
            stats["no_pdf"] += 1
            continue

        print(f"  Parsing: {pdf_rel}")
        meta = parse_abstract_pdf(pdf_path)

        if not meta:
            print(f"    -> [FAIL] could not extract text")
            stats["failed"] += 1
            continue

        changed = []
        for key in ("title", "title_en", "advisor", "keywords", "abstract", "abstract_en"):
            # Map internal key name → index.json key name
            json_key = key
            val = meta.get(key, "")
            if val and not entry.get(json_key, "").strip():
                entry[json_key] = val
                changed.append(json_key)
            elif val and force:
                entry[json_key] = val
                changed.append(json_key)

        if changed:
            stats["updated"] += 1
            print(f"    -> OK: {', '.join(changed)}")
        else:
            stats["skipped"] += 1
            print(f"    -> no new fields extracted")

    if not dry_run and stats["updated"] > 0:
        idx_data["entries"] = entries
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(idx_data, f, ensure_ascii=False, indent=2)
        print(f"  Saved {index_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract thesis metadata from Abstract PDFs")
    parser.add_argument("--year", type=int, help="Process only this year")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing non-empty fields")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be extracted without saving")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN] No files will be saved.\n")

    if args.year:
        years = [args.year]
    else:
        years = sorted(
            int(p.name) for p in THESIS_BASE.iterdir()
            if p.is_dir() and p.name.isdigit()
        )

    total_updated = 0
    for year in years:
        print(f"\n=== Year {year} ===")
        stats = process_year(year, force=args.force, dry_run=args.dry_run)
        total_updated += stats.get("updated", 0)
        print(f"  Total: {stats.get('total',0)} | Updated: {stats.get('updated',0)} "
              f"| Skipped: {stats.get('skipped',0)} | No PDF: {stats.get('no_pdf',0)} "
              f"| Failed: {stats.get('failed',0)}")

    print(f"\n=== DONE: {total_updated} entries updated ===")


if __name__ == "__main__":
    main()

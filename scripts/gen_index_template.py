#!/usr/bin/env python3
"""
Generates docs/thesis/<YEAR>/index.json template files for each year.

Pre-fills file paths from existing folder structure.
For 2556-2560 (old format), extracts title from folder name.
For 2561+, leaves title blank for manual fill.

Usage:
    python scripts/gen_index_template.py              # generate for all years
    python scripts/gen_index_template.py --year 2566  # one year only
    python scripts/gen_index_template.py --force       # overwrite existing
"""
import os
import re
import json
import argparse
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent.parent
THESIS_ROOT = BASE_DIR / "docs" / "thesis"


def normalize_program(prog_folder: str) -> str:
    folder = prog_folder.lower()
    if "geo" in folder:
        return "GEO"
    return "NRE"


def extract_num(folder_name: str) -> str:
    """'010_...' or '01.name' or '01 name' → '010'"""
    m = re.match(r"^(\d+)", folder_name.strip())
    return m.group(1) if m else ""


def extract_title_old(folder_name: str) -> str:
    """Old format '010_Title_studentname' → 'Title'"""
    # Strip leading digits and separator
    s = re.sub(r"^\d+[_\. ]", "", folder_name).strip()
    # Strip trailing _studentname (Thai name after last underscore), only if looks like a name
    # Keep it safe: return the full cleaned string; admin can trim if needed
    return s


def find_pdfs(thesis_folder: Path):
    """Return (abstract_rel, fullpaper_rel) relative to THESIS_ROOT, or None."""
    abstract = fullpaper = other_pdf = None
    for f in sorted(thesis_folder.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".pdf":
            continue
        name_lower = f.name.lower()
        rel = str(f.relative_to(THESIS_ROOT)).replace("\\", "/")
        if "abstract" in name_lower:
            abstract = rel
        elif "fullpaper" in name_lower or "full" in name_lower:
            fullpaper = rel
        elif other_pdf is None:
            other_pdf = rel  # 2568-style: just one PDF named after student
    # If no specific abstract found, use the lone PDF as abstract
    if abstract is None:
        abstract = other_pdf
    return abstract, fullpaper


def process_year(year_dir: Path, force: bool) -> int:
    year_int = int(year_dir.name)
    index_path = year_dir / "index.json"
    is_old = year_int <= 2560

    if index_path.exists() and not force:
        print(f"[SKIP] {year_dir.name}/index.json already exists (--force to overwrite)")
        return 0

    entries = []
    for prog_folder in sorted(year_dir.iterdir()):
        if not prog_folder.is_dir():
            continue
        program = normalize_program(prog_folder.name)

        for thesis_folder in sorted(prog_folder.iterdir()):
            if not thesis_folder.is_dir():
                continue
            folder_name = thesis_folder.name
            num = extract_num(folder_name)
            abstract_pdf, fullpaper_pdf = find_pdfs(thesis_folder)
            title = extract_title_old(folder_name) if is_old else ""

            entries.append({
                "num": num,
                "program": program,
                "title": title,
                "title_en": "",
                "abstract": "",
                "abstract_en": "",
                "advisor": "",
                "keywords": "",
                "abstract_pdf": abstract_pdf,
                "fullpaper_pdf": fullpaper_pdf
            })

    entries.sort(key=lambda e: (e["program"], e["num"].zfill(5)))

    data = {
        "year": year_int,
        "_note": (
            "Fill in title, title_en, advisor, abstract, abstract_en, keywords for each entry. "
            "abstract_pdf and fullpaper_pdf are paths relative to docs/thesis/ and must NOT be changed."
        ),
        "entries": entries
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {year_dir.name}/index.json — {len(entries)} entries written")
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description="Generate index.json templates for docs/thesis")
    parser.add_argument("--year", type=int, help="Process only this year (e.g. 2566)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing index.json files")
    args = parser.parse_args()

    if not THESIS_ROOT.exists():
        print(f"ERROR: docs/thesis not found at {THESIS_ROOT}")
        return

    total = 0
    for year_dir in sorted(THESIS_ROOT.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year_int = int(year_dir.name)
        except ValueError:
            continue
        if args.year and year_int != args.year:
            continue
        total += process_year(year_dir, args.force)

    print(f"\nDone. {total} entries total across all processed years.")
    print("Next step: fill in title/advisor/keywords in each docs/thesis/<YEAR>/index.json")
    print("Then run: python scripts/import_thesis.py --dry-run")


if __name__ == "__main__":
    main()

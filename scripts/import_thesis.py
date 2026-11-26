#!/usr/bin/env python3
"""
Imports thesis entries from docs/thesis/<YEAR>/index.json into api.undergrad_thesis.

Rules:
  - Skips entries where abstract_pdf path is missing.
  - Skips entries where the constructed file_url already exists in DB.
  - Inserts all others.

Usage:
    python scripts/import_thesis.py                   # import all years
    python scripts/import_thesis.py --year 2566       # one year only
    python scripts/import_thesis.py --dry-run         # preview without DB changes
    python scripts/import_thesis.py --dry-run --year 2566
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent
THESIS_ROOT = BASE_DIR / "docs" / "thesis"

# Add app to path
sys.path.insert(0, str(BASE_DIR))


async def run(args):
    # Read DATABASE_URL from .env directly (no pydantic_settings needed)
    env_file = BASE_DIR / ".env"
    db_url = None
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
                break
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        sys.exit(1)

    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg not installed. Run: pip install asyncpg")
        sys.exit(1)

    conn = await asyncpg.connect(db_url)
    print(f"Connected to DB: {db_url.split('@')[-1]}")  # hide credentials

    # Load existing file_urls for duplicate check
    rows = await conn.fetch(
        "SELECT file_url FROM api.undergrad_thesis WHERE file_url IS NOT NULL"
    )
    existing_urls: set = {r["file_url"] for r in rows}
    print(f"Existing thesis in DB: {len(existing_urls)}\n")

    total_inserted = total_skipped = total_errors = 0

    for year_dir in sorted(THESIS_ROOT.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year_int = int(year_dir.name)
        except ValueError:
            continue
        if args.year and year_int != args.year:
            continue

        index_path = year_dir / "index.json"
        if not index_path.exists():
            print(f"[WARN] {year_dir.name}/index.json not found — run gen_index_template.py first")
            continue

        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", [])
        inserted_this_year = skipped_this_year = 0

        for entry in entries:
            abstract_pdf = (entry.get("abstract_pdf") or "").strip()
            # Prefer abstract_pdf, fall back to fullpaper_pdf
            fullpaper_pdf = (entry.get("fullpaper_pdf") or "").strip()
            pdf_path = abstract_pdf or fullpaper_pdf
            if not pdf_path:
                total_skipped += 1
                skipped_this_year += 1
                continue

            # URL served by FastAPI via StaticFiles mounted at /docs
            file_url = f"/docs/thesis/{pdf_path}"

            # fullpaper_url (optional second PDF)
            fullpaper_pdf = (entry.get("fullpaper_pdf") or "").strip()
            fullpaper_url = f"/docs/thesis/{fullpaper_pdf}" if fullpaper_pdf else None

            if file_url in existing_urls:
                total_skipped += 1
                skipped_this_year += 1
                continue

            # Fallback title: use abstract_pdf stem if title is empty
            title = (entry.get("title") or "").strip()
            if not title:
                title = Path(abstract_pdf).stem  # e.g. nre_2566_010_Abstract
                print(f"  [WARN] year={year_int} num={entry.get('num')} program={entry.get('program')}"
                      f" — title blank, using filename: {title}")

            if args.dry_run:
                label = f"program={entry.get('program')} year={year_int} num={entry.get('num')}"
                print(f"  [DRY-RUN] {label} → {title[:60]}")
                total_inserted += 1
                inserted_this_year += 1
                continue

            try:
                await conn.execute(
                    """
                    INSERT INTO api.undergrad_thesis
                        (title, title_en, abstract, abstract_en,
                         advisor, program, keywords, year, file_url, fullpaper_url)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    """,
                    title,
                    entry.get("title_en") or None,
                    entry.get("abstract") or None,
                    entry.get("abstract_en") or None,
                    entry.get("advisor") or None,
                    (entry.get("program") or "NRE").upper(),
                    entry.get("keywords") or None,
                    year_int,
                    file_url,
                    fullpaper_url,
                )
                existing_urls.add(file_url)
                total_inserted += 1
                inserted_this_year += 1
            except Exception as exc:
                print(f"  [ERROR] {file_url}: {exc}")
                total_errors += 1

        print(f"Year {year_int}: inserted={inserted_this_year} skipped={skipped_this_year}")

    await conn.close()

    print()
    print("=" * 50)
    if args.dry_run:
        print("DRY-RUN summary (nothing was written to DB):")
    else:
        print("Import complete:")
    print(f"  Would insert / Inserted : {total_inserted}")
    print(f"  Skipped (dup or no PDF) : {total_skipped}")
    print(f"  Errors                  : {total_errors}")

    if not args.dry_run and total_inserted > 0:
        print("\nThesis entries are now available at /thesis and in the Admin dashboard.")


def main():
    parser = argparse.ArgumentParser(description="Import thesis metadata from index.json into DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB changes")
    parser.add_argument("--year", type=int, help="Import only this year (e.g. 2566)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

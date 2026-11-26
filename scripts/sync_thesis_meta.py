#!/usr/bin/env python3
"""
Sync thesis metadata from index.json → database (UPDATE only, no INSERT).
Reads every index.json and updates advisor, abstract, abstract_en,
title_en, keywords, keywords_en, fullpaper_url for existing rows.

Usage:
    python scripts/sync_thesis_meta.py              # sync all years
    python scripts/sync_thesis_meta.py --year 2566  # one year
    python scripts/sync_thesis_meta.py --dry-run    # preview only
"""
import os, sys, json, asyncio, argparse
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
THESIS = BASE / "docs" / "thesis"
sys.path.insert(0, str(BASE))


async def run(args):
    env_file = BASE / ".env"
    db_url = None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL=") and not line.startswith("#"):
            db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            break
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env"); sys.exit(1)

    import asyncpg
    conn = await asyncpg.connect(db_url)
    print(f"Connected: {db_url.split('@')[-1]}\n")

    # โหลด mapping: file_url → id
    rows = await conn.fetch(
        "SELECT id, file_url FROM api.undergrad_thesis WHERE file_url IS NOT NULL"
    )
    url_to_id = {r["file_url"]: r["id"] for r in rows}
    print(f"Rows in DB: {len(url_to_id)}\n")

    total_updated = total_skipped = 0

    for year_dir in sorted(THESIS.iterdir()):
        if not year_dir.is_dir(): continue
        try: year = int(year_dir.name)
        except: continue
        if args.year and year != args.year: continue

        idx = year_dir / "index.json"
        if not idx.exists(): continue
        entries = json.loads(idx.read_text(encoding="utf-8"))["entries"]

        updated_this_year = 0
        for e in entries:
            abs_pdf  = (e.get("abstract_pdf")  or "").strip()
            full_pdf = (e.get("fullpaper_pdf") or "").strip()
            pdf_path = abs_pdf or full_pdf
            if not pdf_path: continue

            file_url     = f"/docs/thesis/{pdf_path}"
            fullpaper_url = f"/docs/thesis/{full_pdf}" if full_pdf else None

            row_id = url_to_id.get(file_url)
            if row_id is None:
                total_skipped += 1
                continue

            if args.dry_run:
                adv = (e.get("advisor") or "")[:40]
                print(f"  [DRY] id={row_id} {year} {e.get('program')} #{e.get('num')} advisor={adv}")
                total_updated += 1
                updated_this_year += 1
                continue

            await conn.execute("""
                UPDATE api.undergrad_thesis SET
                    title_en      = COALESCE(NULLIF($1,''), title_en),
                    advisor       = COALESCE(NULLIF($2,''), advisor),
                    keywords      = COALESCE(NULLIF($3,''), keywords),
                    abstract      = COALESCE(NULLIF($4,''), abstract),
                    abstract_en   = COALESCE(NULLIF($5,''), abstract_en),
                    fullpaper_url = COALESCE($6, fullpaper_url),
                    updated_at    = NOW()
                WHERE id = $7
            """,
                e.get("title_en")   or "",
                e.get("advisor")    or "",
                e.get("keywords")   or "",
                e.get("abstract")   or "",
                e.get("abstract_en") or "",
                fullpaper_url,
                row_id,
            )
            total_updated += 1
            updated_this_year += 1

        if updated_this_year:
            print(f"  Year {year}: updated {updated_this_year}")

    await conn.close()
    print(f"\n{'[DRY-RUN] Would update' if args.dry_run else 'Updated'}: {total_updated}")
    print(f"Skipped (not in DB): {total_skipped}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year",    type=int)
    p.add_argument("--dry-run", action="store_true")
    asyncio.run(run(p.parse_args()))

main()

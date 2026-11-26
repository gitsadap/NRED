#!/usr/bin/env python3
"""
migrate_thesis.py
-----------------
Run on Mac (device_bash). Does 4 things:
1. Parse all webNRED-old PHP files → extract thesis metadata
2. Copy PDFs from webNRED-old/Document/is-PDF/<year>/ to docs/thesis/<year>/ (flat)
3. Flatten existing docs/thesis/<year>/<sub>/<num.name>/*.pdf to docs/thesis/<year>/
4. Generate/regenerate docs/thesis/<year>/index.json for ALL years

Usage: cd ~/mnt/agi && python3 scripts/migrate_thesis.py
"""
import os, re, json, shutil
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
WOLD = HOME / "mnt/webNRED-old"
OLD_PDF_BASE = WOLD / "Document/is-PDF"
THESIS_BASE = HOME / "mnt/agi/docs/thesis"

# ---------------------------------------------------------------------------
# HTML table row parser (regex-based, no external deps)
# ---------------------------------------------------------------------------

def clean_html(s):
    """Strip HTML tags and normalize whitespace."""
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'&nbsp;', ' ', s)
    s = re.sub(r'&[a-z]+;', '', s)
    return re.sub(r'\s+', ' ', s).strip().lstrip('\xa0 ')


def parse_php(path, program, year):
    """Parse a PHP file, return list of entry dicts."""
    with open(path, "rb") as f:
        content = f.read().decode("cp874", errors="replace")
    
    entries = []
    
    # Match each <tr>...</tr> block
    tr_blocks = re.findall(r'<tr\b[^>]*>.*?</tr>', content, re.DOTALL | re.IGNORECASE)
    
    for block in tr_blocks:
        # Must have PDF link
        pdf_links = re.findall(
            r'href="[^"]*Document/is-PDF/(\d+)/([^"]+\.pdf)"',
            block, re.IGNORECASE
        )
        if not pdf_links:
            continue
        
        # Get td texts
        tds = re.findall(r'<td\b[^>]*>(.*?)</td>', block, re.DOTALL | re.IGNORECASE)
        texts = [clean_html(td) for td in tds]
        
        if len(texts) < 2:
            continue
        
        # First td should be a small number (1-150)
        num_text = texts[0].strip()
        if not re.match(r'^\d{1,3}$', num_text):
            continue
        num_int = int(num_text)
        if num_int == 0 or num_int > 150:
            continue
        
        title = texts[1].strip() if len(texts) > 1 else ""
        author = texts[2].strip() if len(texts) > 2 else ""
        
        if len(title) < 4:
            continue
        
        # Collect PDF paths from this year only
        abstract_pdf = None
        fullpaper_pdf = None
        for yr, fname in pdf_links:
            fn_lower = fname.lower()
            flat = f"{yr}/{fname}"
            if "abstract" in fn_lower or "-th" in fn_lower:
                if abstract_pdf is None:
                    abstract_pdf = flat
            elif "fullpaper" in fn_lower or "-en" in fn_lower:
                if fullpaper_pdf is None:
                    fullpaper_pdf = flat
            else:
                # unrecognized: first = abstract, second = fullpaper
                if abstract_pdf is None:
                    abstract_pdf = flat
                elif fullpaper_pdf is None:
                    fullpaper_pdf = flat
        
        entries.append({
            "num_int": num_int,
            "program": program.upper(),
            "title": title,
            "author": author,
            "abstract_pdf_raw": abstract_pdf,
            "fullpaper_pdf_raw": fullpaper_pdf,
        })
    
    # Deduplicate by num_int
    seen = set()
    unique = []
    for e in entries:
        if e["num_int"] not in seen:
            seen.add(e["num_int"])
            unique.append(e)
    
    return sorted(unique, key=lambda x: x["num_int"])


def parse_geo_old_by_year(path, year):
    """Parse is-2529-2554bs_geo.php - handles 5-column format (year, num, title, author, link).
    Tracks current_year as we scan rows so we capture entries even when PDF links reference
    a different folder name than the logical year.
    """
    with open(path, "rb") as f:
        content = f.read().decode("cp874", errors="replace")
    
    year_str = str(year)
    tr_blocks = re.findall(r'<tr\b[^>]*>.*?</tr>', content, re.DOTALL | re.IGNORECASE)
    
    all_entries = []
    current_year = None
    
    for block in tr_blocks:
        tds = re.findall(r'<td\b[^>]*>(.*?)</td>', block, re.DOTALL | re.IGNORECASE)
        texts = [clean_html(td) for td in tds]
        hrefs = re.findall(r'href="([^"]+\.pdf)"', block, re.IGNORECASE)
        
        if len(texts) < 3:
            continue
        
        t0 = texts[0].strip()
        t1 = texts[1].strip() if len(texts) > 1 else ""
        
        # Pattern A: [year, num, title, author, ...] — 5-column, year header + entry
        if re.match(r'^2[5-6]\d\d$', t0) and re.match(r'^\d{1,2}$', t1):
            current_year = int(t0)
            num_int = int(t1)
            title = texts[2].strip() if len(texts) > 2 else ""
            author = texts[3].strip() if len(texts) > 3 else ""
        # Pattern B: [empty, num, title, author, ...] — continuation of same year
        elif (not t0 or not re.search(r'\S', t0)) and re.match(r'^\d{1,2}$', t1):
            if current_year is None:
                continue
            num_int = int(t1)
            title = texts[2].strip() if len(texts) > 2 else ""
            author = texts[3].strip() if len(texts) > 3 else ""
        # Pattern C: [num, title, author, ...] — 4-column format
        elif re.match(r'^\d{1,2}$', t0) and len(texts) > 1 and len(texts[1]) > 4:
            if current_year is None:
                continue
            num_int = int(t0)
            title = texts[1].strip()
            author = texts[2].strip() if len(texts) > 2 else ""
        else:
            # Year section header or unrecognised row; update current_year if applicable
            if re.match(r'^2[5-6]\d\d$', t0):
                current_year = int(t0)
            continue
        
        if num_int < 1 or num_int > 100 or len(title) < 4:
            continue
        
        # Only collect entries for the requested year
        if current_year != year:
            continue
        
        # Extract PDF paths from href attributes
        abs_pdf = None
        full_pdf = None
        for href in hrefs:
            fname = href.split('/')[-1]
            fn_lower = fname.lower()
            if 'abstract' in fn_lower or '-th' in fn_lower:
                if abs_pdf is None: abs_pdf = f"{year_str}/{fname}"
            elif 'fullpaper' in fn_lower or 'full' in fn_lower or '-en' in fn_lower:
                if full_pdf is None: full_pdf = f"{year_str}/{fname}"
            else:
                if abs_pdf is None: abs_pdf = f"{year_str}/{fname}"
                elif full_pdf is None: full_pdf = f"{year_str}/{fname}"
        
        all_entries.append({
            "num_int": num_int,
            "program": "GEO",
            "title": title,
            "author": author,
            "abstract_pdf_raw": abs_pdf,
            "fullpaper_pdf_raw": full_pdf,
        })
    
    # Deduplicate by num_int (keep first occurrence)
    seen = set()
    unique = []
    for e in all_entries:
        if e["num_int"] not in seen:
            seen.add(e["num_int"])
            unique.append(e)
    
    return sorted(unique, key=lambda x: x["num_int"])


def build_php_map():
    result = {}
    for year in range(2556, 2569):
        for prog in ("nre", "geo"):
            path = WOLD / f"is-{year}bs_{prog}.php"
            if path.exists():
                result[(prog, year)] = str(path)
    
    # 2555: combined
    p2555 = WOLD / "is-2555bs.php"
    if p2555.exists():
        result[("geo", 2555)] = str(p2555)
        result[("nre", 2555)] = str(p2555)
    
    # 2550–2554 NRE grad
    for year in range(2550, 2555):
        p = WOLD / f"is-{year}.php"
        if p.exists():
            result[("nre", year)] = str(p)
    
    # GEO 2529–2554 big file
    pgeo = WOLD / "is-2529-2554bs_geo.php"
    if pgeo.exists():
        for year in [2529,2533,2538,2539,2540,2541,2543,2544,2545,2546,2547,2548,2549,2550,2553,2554]:
            result[("geo", year)] = str(pgeo)
    
    return result


# ---------------------------------------------------------------------------
# Find actual flat PDF path
# ---------------------------------------------------------------------------

def find_flat_pdf(year, program, num_int, kind):
    """Look for existing PDF file in flat docs/thesis/<year>/ folder."""
    year_dir = THESIS_BASE / str(year)
    if not year_dir.exists():
        return None
    
    prog = program.lower()
    year_str = str(year)
    
    # Number patterns used in filenames
    if num_int < 10:
        num_patterns = [f"0{num_int}"]
    else:
        num_patterns = [f"0{num_int}", f"{num_int:03d}", str(num_int)]
    
    if kind == "abstract":
        suffixes = ["Abstract.pdf", "abstract.pdf"]
    else:
        suffixes = ["FullPaper.pdf", "fullpaper.pdf", "Full.pdf"]
    
    # Pattern A: prog_year_NUM_Kind.pdf
    for num_s in num_patterns:
        for suf in suffixes:
            fname = f"{prog}_{year_str}_{num_s}_{suf}"
            if (year_dir / fname).exists():
                return f"{year_str}/{fname}"
    
    # Pattern B: NUM-YEAR-th/en.pdf (old NRE grad)
    for num_s in num_patterns:
        if kind == "abstract":
            fname = f"{num_s}-{year_str}-th.pdf"
        else:
            fname = f"{num_s}-{year_str}-en.pdf"
        if (year_dir / fname).exists():
            return f"{year_str}/{fname}"
    
    return None


# ---------------------------------------------------------------------------
# Steps 1 & 2: Copy/Flatten PDFs
# ---------------------------------------------------------------------------

def copy_old_pdfs():
    """Copy PDFs from webNRED-old to docs/thesis/<year>/ (flat).
    Also copies from ป.โท/ subfolders (NRE master's theses in 2553-2554).
    """
    if not OLD_PDF_BASE.exists():
        return
    for year_dir in sorted(OLD_PDF_BASE.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        dest_dir = THESIS_BASE / str(year)
        dest_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        # Copy PDFs at year root level
        for pdf in year_dir.glob("*.pdf"):
            dest = dest_dir / pdf.name
            if not dest.exists():
                shutil.copy2(str(pdf), str(dest))
                copied += 1
        # Copy PDFs from ป.โท/ subfolder (NRE grad 2553-2554)
        potho_dir = year_dir / "ป.โท"
        if potho_dir.exists() and potho_dir.is_dir():
            for pdf in potho_dir.glob("*.pdf"):
                dest = dest_dir / pdf.name
                if not dest.exists():
                    shutil.copy2(str(pdf), str(dest))
                    copied += 1
        if copied:
            print(f"  Copied {copied} PDFs → thesis/{year}/")


def flatten_nested():
    for year_dir in sorted(THESIS_BASE.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            int(year_dir.name)
        except ValueError:
            continue
        copied = 0
        for pdf in year_dir.rglob("*.pdf"):
            if pdf.parent == year_dir:
                continue
            dest = year_dir / pdf.name
            if not dest.exists():
                shutil.copy2(str(pdf), str(dest))
                copied += 1
        if copied:
            print(f"  Flattened {copied} PDFs in thesis/{year_dir.name}/")


# ---------------------------------------------------------------------------
# Step 3: Generate index.json
# ---------------------------------------------------------------------------

def build_index(year, php_entries):
    entries = []
    for e in php_entries:
        num_int = e["num_int"]
        prog = e["program"]
        
        # Try to find actual PDF file
        abs_pdf = find_flat_pdf(year, prog, num_int, "abstract")
        full_pdf = find_flat_pdf(year, prog, num_int, "fullpaper")
        
        # Fallback: use raw path from PHP if file exists
        if not abs_pdf and e.get("abstract_pdf_raw"):
            p = THESIS_BASE / e["abstract_pdf_raw"]
            if p.exists():
                abs_pdf = e["abstract_pdf_raw"]
        if not full_pdf and e.get("fullpaper_pdf_raw"):
            p = THESIS_BASE / e["fullpaper_pdf_raw"]
            if p.exists():
                full_pdf = e["fullpaper_pdf_raw"]
        
        # GEO fallback: use fullpaper as abstract
        if not abs_pdf and full_pdf:
            abs_pdf = full_pdf
        
        num_str = f"0{num_int}" if num_int < 10 else f"0{num_int}"
        
        entries.append({
            "num": num_str,
            "program": prog,
            "title": e.get("title", ""),
            "title_en": "",
            "author": e.get("author", ""),
            "abstract": "",
            "abstract_en": "",
            "advisor": "",
            "keywords": "",
            "abstract_pdf": abs_pdf,
            "fullpaper_pdf": full_pdf,
        })
    
    return entries


def scan_extra_pdfs(year, entries):
    """Find PDFs in flat dir not covered by entries."""
    year_dir = THESIS_BASE / str(year)
    if not year_dir.exists():
        return
    
    registered = set()
    for e in entries:
        for key in ("abstract_pdf", "fullpaper_pdf"):
            if e.get(key):
                registered.add(os.path.basename(e[key]))
    
    for pdf in sorted(year_dir.glob("*.pdf")):
        if pdf.name in registered:
            continue
        # Try prog_year_num_kind.pdf
        m = re.match(
            rf'^(nre|geo)_{year}_(0?\d+)_(Abstract|FullPaper)\.pdf$',
            pdf.name, re.IGNORECASE
        )
        if m:
            prog = m.group(1).upper()
            num_int = int(m.group(2).lstrip("0") or "0")
            kind = m.group(3).lower()
            num_str = f"0{num_int}" if num_int < 10 else f"0{num_int}"
            rel = f"{year}/{pdf.name}"
            # Find existing entry
            existing = next((e for e in entries
                           if e["program"] == prog and e["num"] == num_str), None)
            if existing:
                if kind == "abstract" and not existing["abstract_pdf"]:
                    existing["abstract_pdf"] = rel
                elif kind == "fullpaper" and not existing["fullpaper_pdf"]:
                    existing["fullpaper_pdf"] = rel
            else:
                entries.append({
                    "num": num_str,
                    "program": prog,
                    "title": "",
                    "title_en": "",
                    "author": "",
                    "abstract": "",
                    "abstract_en": "",
                    "advisor": "",
                    "keywords": "",
                    "abstract_pdf": rel if kind == "abstract" else None,
                    "fullpaper_pdf": rel if kind == "fullpaper" else None,
                })
            registered.add(pdf.name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Step 1: Copy PDFs from webNRED-old → docs/thesis/<year>/ ===")
    copy_old_pdfs()
    
    print("\n=== Step 2: Flatten nested docs/thesis structure ===")
    flatten_nested()
    
    print("\n=== Step 3: Parse PHP + generate index.json ===")
    php_map = build_php_map()
    
    all_years = set()
    for (prog, year) in php_map:
        all_years.add(year)
    for d in THESIS_BASE.iterdir():
        if d.is_dir():
            try: all_years.add(int(d.name))
            except ValueError: pass
    
    for year in sorted(all_years):
        print(f"\n--- Year {year} ---")
        
        php_entries = []
        
        for prog in ("geo", "nre"):
            key = (prog, year)
            if key not in php_map:
                continue
            php_path = php_map[key]
            fname = os.path.basename(php_path)
            if "2529-2554" in fname:
                e_list = parse_geo_old_by_year(php_path, year)
            else:
                e_list = parse_php(php_path, prog, year)
            print(f"  {prog.upper()}: {len(e_list)} from PHP")
            php_entries.extend(e_list)
        
        entries = build_index(year, php_entries)
        scan_extra_pdfs(year, entries)
        
        # Sort: GEO first, then NRE; by num within program
        def sort_key(e):
            p = 0 if e["program"] == "GEO" else 1
            n = int(e["num"].lstrip("0") or "0")
            return (p, n)
        entries.sort(key=sort_key)
        
        if not entries:
            print(f"  [SKIP] No data")
            continue
        
        year_dir = THESIS_BASE / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        
        index_path = year_dir / "index.json"
        with open(str(index_path), "w", encoding="utf-8") as f:
            json.dump({"year": year, "entries": entries}, f, ensure_ascii=False, indent=2)
        
        with_pdf = sum(1 for e in entries if e.get("abstract_pdf") or e.get("fullpaper_pdf"))
        print(f"  → index.json: {len(entries)} entries ({with_pdf} with PDF)")
    
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()

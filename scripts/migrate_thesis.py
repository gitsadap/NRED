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
    """Parse a PHP file by scanning ALL <td> elements in document order.
    
    For each <td> containing a PDF href for the requested year:
    - Entry number is extracted from the PDF filename
    - Title comes from the <td> two positions before the PDF cell
    - Author comes from the <td> one position before the PDF cell
    
    This handles multi-entry rows (where PHP packs several entries into one <tr>)
    which the old row-by-row parser missed entirely.
    """
    with open(path, "rb") as f:
        content = f.read().decode("cp874", errors="replace")
    
    # Remove HTML comments (entries commented out with <!-- --> are excluded)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    year_str = str(year)
    
    # Get all <td> elements in document order (raw HTML + cleaned text)
    td_matches = list(re.finditer(r'<td\b[^>]*>(.*?)</td>', content, re.DOTALL | re.IGNORECASE))
    all_texts = [clean_html(m.group(1)) for m in td_matches]
    all_raw   = [m.group(0) for m in td_matches]
    
    entries_dict = {}  # num_int -> entry dict
    
    for i, raw in enumerate(all_raw):
        # Find PDF links for this year in this cell
        pdf_links = re.findall(
            rf'href="[^"]*Document/is-PDF/{year_str}/([^"]+\.pdf)"',
            raw, re.IGNORECASE
        )
        if not pdf_links:
            continue
        
        # Extract entry number from PDF filename
        num_int = None
        for fname in pdf_links:
            m = re.search(r'(?:nre|geo)_\d+_0*(\d+)_', fname, re.I)
            if m:
                num_int = int(m.group(1)); break
            # Old NRE grad format: NN-YYYY-th.pdf
            m = re.search(r'^0*(\d+)-\d{4}-(?:th|en)\.pdf', fname, re.I)
            if m:
                num_int = int(m.group(1)); break
        
        if num_int is None or num_int < 1 or num_int > 300:
            continue
        
        # Title is 2 cells back, author is 1 cell back
        title = ""
        author = ""
        if i >= 2:
            # Strip trailing entry number that may bleed from adjacent PDF cell
            cand_a = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-1]).strip()
            cand_t = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-2]).strip()
            if len(cand_t) > 4 and not re.match(r'^\d+$', cand_t):
                title  = cand_t
                author = cand_a
        
        # Classify PDF types
        abs_pdf  = None
        full_pdf = None
        for fname in pdf_links:
            fn   = fname.lower()
            flat = f"{year_str}/{fname}"
            if 'abstract' in fn or '-th' in fn:
                if abs_pdf  is None: abs_pdf  = flat
            elif 'fullpaper' in fn or 'full' in fn or '-en' in fn:
                if full_pdf is None: full_pdf = flat
            else:
                if abs_pdf  is None: abs_pdf  = flat
                elif full_pdf is None: full_pdf = flat
        
        if num_int in entries_dict:
            # Already seen this entry — just fill missing PDF path
            e = entries_dict[num_int]
            if full_pdf and not e['fullpaper_pdf_raw']: e['fullpaper_pdf_raw'] = full_pdf
            if abs_pdf  and not e['abstract_pdf_raw']:  e['abstract_pdf_raw']  = abs_pdf
        else:
            entries_dict[num_int] = {
                "num_int":           num_int,
                "program":           program.upper(),
                "title":             title,
                "author":            author,
                "abstract_pdf_raw":  abs_pdf,
                "fullpaper_pdf_raw": full_pdf,
            }
    
    return sorted(entries_dict.values(), key=lambda x: x["num_int"])


def parse_geo_old_by_year(path, year):
    """Parse is-2529-2554bs_geo.php using td-sequence scanning.
    
    Entry number and year are extracted from PDF filename (geo_YYYY_NN_FullPaper.pdf).
    Title is 2 cells back from the PDF cell, author is 1 cell back.
    Handles 5-column format (year header + entry in same row) automatically.
    """
    with open(path, "rb") as f:
        content = f.read().decode("cp874", errors="replace")
    
    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    year_str = str(year)
    
    td_matches = list(re.finditer(r'<td\b[^>]*>(.*?)</td>', content, re.DOTALL | re.IGNORECASE))
    all_texts  = [clean_html(m.group(1)) for m in td_matches]
    all_raw    = [m.group(0) for m in td_matches]
    
    entries_dict = {}
    
    for i, raw in enumerate(all_raw):
        # Look for GEO PDF links for this year
        pdf_links = re.findall(
            r'href="[^"]*Document/is-PDF/(\d{4})/([^"]+\.pdf)"',
            raw, re.IGNORECASE
        )
        if not pdf_links:
            continue
        
        # Filter to this year
        year_links = [(yr, fn) for yr, fn in pdf_links if int(yr) == year]
        if not year_links:
            continue
        
        # Extract entry number from PDF filename
        num_int = None
        for yr, fname in year_links:
            m = re.search(r'geo_\d+_0*(\d+)_', fname, re.I)
            if m:
                num_int = int(m.group(1)); break
        
        if num_int is None or num_int < 1 or num_int > 100:
            continue
        
        # Title is 2 cells back, author is 1 cell back
        # (In 5-column rows the year cell was before that, but it doesn't interfere)
        title = ""
        author = ""
        if i >= 2:
            cand_a = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-1]).strip()
            cand_t = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-2]).strip()
            # Skip year header cell as title (e.g. "2529")
            if re.match(r'^2[5-6]\d\d$', cand_t):
                # 5-column format: year|num|title|author|pdf — author is at i-1, title at i-2 is num
                # Try going one more back
                if i >= 3:
                    cand_a2 = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-2]).strip()
                    cand_t2 = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-3]).strip()
                    if not re.match(r'^2[5-6]\d\d$', cand_t2) and not re.match(r'^\d{1,2}$', cand_t2) and len(cand_t2) > 4:
                        title  = cand_t2
                        author = cand_a2
            elif len(cand_t) > 4 and not re.match(r'^\d+$', cand_t):
                title  = cand_t
                author = cand_a
        
        # Classify PDFs
        abs_pdf  = None
        full_pdf = None
        for yr, fname in year_links:
            fn   = fname.lower()
            flat = f"{yr}/{fname}"
            if 'abstract' in fn:
                if abs_pdf  is None: abs_pdf  = flat
            elif 'fullpaper' in fn or 'full' in fn:
                if full_pdf is None: full_pdf = flat
            else:
                if full_pdf is None: full_pdf = flat  # GEO old = FullPaper
        
        if num_int in entries_dict:
            e = entries_dict[num_int]
            if full_pdf and not e['fullpaper_pdf_raw']: e['fullpaper_pdf_raw'] = full_pdf
            if abs_pdf  and not e['abstract_pdf_raw']:  e['abstract_pdf_raw']  = abs_pdf
        else:
            entries_dict[num_int] = {
                "num_int":           num_int,
                "program":           "GEO",
                "title":             title,
                "author":            author,
                "abstract_pdf_raw":  abs_pdf,
                "fullpaper_pdf_raw": full_pdf,
            }
    
    return sorted(entries_dict.values(), key=lambda x: x["num_int"])



# ---------------------------------------------------------------------------
# PHP file mapping
# ---------------------------------------------------------------------------

def build_php_map():
    result = {}
    for year in range(2556, 2569):
        for prog in ("nre", "geo"):
            path = WOLD / f"is-{year}bs_{prog}.php"
            if path.exists():
                result[(prog, year)] = str(path)
    
    # 2555: combined file
    p2555 = WOLD / "is-2555bs.php"
    if p2555.exists():
        result[("geo", 2555)] = str(p2555)
        result[("nre", 2555)] = str(p2555)
    
    # 2550-2554 NRE grad
    for year in range(2550, 2555):
        p = WOLD / f"is-{year}.php"
        if p.exists():
            result[("nre", year)] = str(p)
    
    # GEO 2529-2554 big file
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

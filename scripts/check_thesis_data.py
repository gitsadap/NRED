#!/usr/bin/env python3
"""
ตรวจสอบความถูกต้องของข้อมูล thesis:
  1. เปรียบเทียบ title ใน index.json กับ PHP source
  2. รายงาน advisor names ทั้งหมดที่มี (จาก DB)
  3. รายงานชื่อที่อาจสะกดผิด (duplicates ที่ต่างกันเล็กน้อย)

Usage:
    python scripts/check_thesis_data.py          # รายงาน advisor + title diff
    python scripts/check_thesis_data.py --title  # เฉพาะ title check
    python scripts/check_thesis_data.py --advisor  # เฉพาะ advisor list
"""
import os, sys, re, json, asyncio, argparse
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
WOLD   = Path("C:/Users/NRED/webNRED-old") if sys.platform == "win32" else \
         Path("/Volumes/DATA/webNRED-old")
THESIS = BASE / "docs" / "thesis"


# ───── PHP helpers (same as migrate_thesis) ─────────────────────────────────
def clean_html(h):
    h = re.sub(r'<[^>]+>', ' ', h)
    h = re.sub(r'&nbsp;', ' ', h, flags=re.I)
    h = re.sub(r'&amp;', '&', h, flags=re.I)
    h = re.sub(r'&lt;', '<', h, flags=re.I)
    h = re.sub(r'&gt;', '>', h, flags=re.I)
    h = re.sub(r'&#\d+;', '', h)
    return re.sub(r'\s+', ' ', h).strip()


def php_titles(path, year, program):
    """ดึงเฉพาะ {num_int: title} จาก PHP"""
    with open(path, "rb") as f:
        content = f.read().decode("cp874", errors="replace")
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    year_str = str(year)

    td_matches = list(re.finditer(r'<td\b[^>]*>(.*?)</td>', content, re.DOTALL | re.IGNORECASE))
    all_texts  = [clean_html(m.group(1)) for m in td_matches]
    all_raw    = [m.group(0) for m in td_matches]

    result = {}
    for i, raw in enumerate(all_raw):
        if program == "geo_old":
            pdf_links = re.findall(r'href="[^"]*Document/is-PDF/(\d{4})/([^"]+\.pdf)"',
                                   raw, re.IGNORECASE)
            year_links = [(yr, fn) for yr, fn in pdf_links if int(yr) == year]
            if not year_links: continue
            num_int = None
            for yr, fn in year_links:
                m = re.search(r'geo_\d+_0*(\d+)_', fn, re.I)
                if m: num_int = int(m.group(1)); break
        else:
            pdf_links = re.findall(
                rf'href="[^"]*Document/is-PDF/{year_str}/([^"]+\.pdf)"', raw, re.IGNORECASE)
            if not pdf_links: continue
            num_int = None
            for fn in pdf_links:
                m = re.search(r'(?:nre|geo)_\d+_0*(\d+)_', fn, re.I)
                if m: num_int = int(m.group(1)); break
                m = re.search(r'^0*(\d+)-\d{4}-(?:th|en)\.pdf', fn, re.I)
                if m: num_int = int(m.group(1)); break

        if num_int is None or not (1 <= num_int <= 300): continue
        if i < 2: continue
        cand_t = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-2]).strip()
        if program == "geo_old" and re.match(r'^2[5-6]\d\d$', cand_t):
            if i >= 3:
                cand_t = re.sub(r'\s+\d{1,3}\s*$', '', all_texts[i-3]).strip()
        if len(cand_t) > 4 and not re.match(r'^\d+$', cand_t):
            result[num_int] = cand_t
    return result


def build_php_map():
    result = {}
    for year in range(2556, 2569):
        for prog in ("nre", "geo"):
            path = WOLD / f"is-{year}bs_{prog}.php"
            if path.exists(): result[(prog, year)] = (str(path), prog)
    p2555 = WOLD / "is-2555bs.php"
    if p2555.exists():
        result[("geo", 2555)] = (str(p2555), "geo")
        result[("nre", 2555)] = (str(p2555), "nre")
    for year in range(2550, 2555):
        p = WOLD / f"is-{year}.php"
        if p.exists(): result[("nre", year)] = (str(p), "nre")
    pgeo = WOLD / "is-2529-2554bs_geo.php"
    if pgeo.exists():
        for y in [2529,2533,2538,2539,2540,2541,2543,2544,2545,2546,2547,2548,2549,2550,2553,2554]:
            result[("geo", y)] = (str(pgeo), "geo_old")
    return result


def check_titles():
    if not WOLD.exists():
        print("[WARN] webNRED-old not found — skipping PHP title compare")
        return
    php_map = build_php_map()
    diffs = []
    for year_dir in sorted(THESIS.iterdir()):
        if not year_dir.is_dir(): continue
        try: year = int(year_dir.name)
        except ValueError: continue
        idx = year_dir / "index.json"
        if not idx.exists(): continue
        entries = json.loads(idx.read_text(encoding="utf-8"))["entries"]

        for prog in ("nre", "geo"):
            key = (prog, year)
            if key not in php_map: continue
            path, prog_type = php_map[key]
            php_t = php_titles(path, year, prog_type)

            for e in entries:
                if e.get("program", "").upper() != prog.upper(): continue
                try: num_int = int(e["num"])
                except: continue
                php_title = php_t.get(num_int, "")
                json_title = e.get("title", "")
                if php_title and json_title and php_title != json_title:
                    diffs.append({
                        "year": year, "prog": prog.upper(), "num": e["num"],
                        "php": php_title, "json": json_title
                    })

    if not diffs:
        print("✅ ชื่องานทุกรายการตรงกับ PHP source")
    else:
        print(f"⚠️  พบ {len(diffs)} รายการที่ชื่อต่างจาก PHP:\n")
        for d in diffs:
            print(f"  {d['year']} {d['prog']} #{d['num']}")
            print(f"    PHP : {d['php']}")
            print(f"    JSON: {d['json']}\n")


async def check_advisors():
    env_file = BASE / ".env"
    db_url = None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL=") and not line.startswith("#"):
            db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            break
    if not db_url:
        print("[WARN] DATABASE_URL not found, reading from index.json instead")
        return _check_advisors_from_json()

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        rows = await conn.fetch(
            "SELECT DISTINCT advisor FROM api.undergrad_thesis WHERE advisor IS NOT NULL AND advisor != '' ORDER BY advisor"
        )
        advisors = [r["advisor"] for r in rows]
        await conn.close()
    except Exception as e:
        print(f"[WARN] DB error: {e} — reading from index.json")
        advisors = _check_advisors_from_json()

    _report_advisors(advisors)


def _check_advisors_from_json():
    adv_set = set()
    for y in sorted(THESIS.iterdir()):
        idx = y / "index.json"
        if not idx.exists(): continue
        for e in json.loads(idx.read_text())["entries"]:
            a = (e.get("advisor") or "").strip()
            if a: adv_set.add(a)
    return sorted(adv_set)


def _report_advisors(advisors):
    if not advisors:
        print("⚠️  ยังไม่มีข้อมูลอาจารย์ที่ปรึกษาในระบบ")
        print("   → รัน extract_thesis_meta.py บน Windows server ก่อน")
        return
    print(f"📋 อาจารย์ที่ปรึกษาทั้งหมด {len(advisors)} ท่าน:\n")
    for a in advisors:
        print(f"  {a}")

    # ตรวจ duplicates ที่อาจสะกดต่างกัน (strip ช่องว่าง / ตัวพิมพ์)
    normalized = {}
    for a in advisors:
        key = re.sub(r'\s+', ' ', a).strip().lower()
        normalized.setdefault(key, []).append(a)
    suspects = {k: v for k, v in normalized.items() if len(v) > 1}
    if suspects:
        print(f"\n⚠️  พบชื่อที่อาจซ้ำ/สะกดต่างกัน {len(suspects)} กลุ่ม:")
        for k, variants in suspects.items():
            print(f"  {variants}")
    else:
        print("\n✅ ไม่พบชื่อที่สะกดซ้ำกัน")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title",   action="store_true")
    parser.add_argument("--advisor", action="store_true")
    args = parser.parse_args()

    do_title   = args.title   or not (args.title or args.advisor)
    do_advisor = args.advisor or not (args.title or args.advisor)

    if do_title:
        print("=" * 60)
        print("📄 ตรวจสอบชื่องาน (index.json vs PHP)")
        print("=" * 60)
        check_titles()

    if do_advisor:
        print("\n" + "=" * 60)
        print("👨‍🏫 รายชื่ออาจารย์ที่ปรึกษา")
        print("=" * 60)
        await check_advisors()

asyncio.run(main())

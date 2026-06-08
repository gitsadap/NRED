import asyncio
import os
import sys
import urllib.request
import re
from bs4 import BeautifulSoup

sys.path.append("/Users/gitsadap/Downloads/agi")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Faculty
from app.config import settings

def clean_name(name_str):
    if not name_str:
        return ""
    # Replace non-breaking spaces
    name_str = name_str.replace("\xa0", " ")
    # Clean prefixes
    prefixes = [
        "ผศ.ดร.", "รศ.ดร.", "ศ.ดร.", "รศ.รอ.ดร.", "รอ.ดร.", 
        "ดร.", "ผศ.", "รศ.", "ศ.", "อาจารย์", "นาย", "นางสาว", "นาง"
    ]
    for p in prefixes:
        if name_str.startswith(p):
            name_str = name_str[len(p):]
    name_str = name_str.strip()
    # Normalize spaces
    name_str = re.sub(r'\s+', ' ', name_str)
    return name_str

async def main():
    # 1. Scrape names and CV links
    url = "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    req = urllib.request.Request(url, headers=headers)
    parsed_teachers = []
    
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read()
            try:
                html_text = html.decode('utf-8')
            except UnicodeDecodeError:
                html_text = html.decode('tis-620', errors='ignore')
            
            soup = BeautifulSoup(html_text, 'html.parser')
            tables = soup.find_all('table', border="4")
            for tbl in tables:
                name = None
                cv_link = None
                rows = tbl.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        col1_text = cols[0].get_text(strip=True)
                        if "ชื่อ" in col1_text:
                            name = cols[1].get_text(strip=True)
                        elif "ประวัติบุคคล" in col1_text:
                            link_tag = cols[1].find('a', href=True)
                            if link_tag:
                                cv_link = link_tag['href']
                if name:
                    parsed_teachers.append({
                        "original_name": name,
                        "cleaned_name": clean_name(name),
                        "cv_link": cv_link
                    })
    except Exception as e:
        print("Scraping error:", e)
        return

    # 2. Get DB faculty
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        res = await db.execute(select(Faculty))
        db_faculties = res.scalars().all()
        
    await engine.dispose()
    
    # 3. Match
    print(f"Scraped {len(parsed_teachers)} teachers. DB has {len(db_faculties)} faculties.")
    print("\n--- Match Results ---")
    
    for pt in parsed_teachers:
        scraped_cleaned = pt["cleaned_name"]
        scraped_parts = scraped_cleaned.split(' ')
        scraped_fname = scraped_parts[0] if len(scraped_parts) > 0 else ""
        scraped_lname = scraped_parts[1] if len(scraped_parts) > 1 else ""
        
        match = None
        # Try exact fname matching
        for f in db_faculties:
            db_fname = clean_name(f.fname)
            db_lname = clean_name(f.lname)
            
            # Simple matching: First name matches exactly, and last name is either empty or matches/substrings
            if scraped_fname == db_fname:
                match = f
                break
            # Fallback check if scraped fname matches substring of db_fname
            elif scraped_fname in db_fname or db_fname in scraped_fname:
                # Double check last name
                if scraped_lname and (scraped_lname in db_lname or db_lname in scraped_lname):
                    match = f
                    break
        
        if match:
            print(f"MATCH: Legacy: '{pt['original_name']}' -> DB: '{match.fname} {match.lname}' (ID: {match.id}) | CV: {pt['cv_link']}")
        else:
            print(f"NO MATCH: Legacy: '{pt['original_name']}' | Cleaned: '{scraped_cleaned}' | CV: {pt['cv_link']}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import sys
import urllib.request
import urllib.parse
import re
import uuid
from bs4 import BeautifulSoup

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Faculty, FacultyCV
from app.config import settings

def clean_name(name_str):
    if not name_str:
        return ""
    name_str = name_str.replace("\xa0", " ")
    prefixes = [
        "ผศ.ดร.", "รศ.ดร.", "ศ.ดร.", "รศ.รอ.ดร.", "รอ.ดร.", 
        "ดร.", "ผศ.", "รศ.", "ศ.", "อาจารย์", "นาย", "นางสาว", "นาง"
    ]
    for p in prefixes:
        if name_str.startswith(p):
            name_str = name_str[len(p):]
    name_str = name_str.strip()
    name_str = re.sub(r'\s+', ' ', name_str)
    return name_str

async def migrate():
    # 1. Scrape names and CV links
    url = "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    req = urllib.request.Request(url, headers=headers)
    parsed_teachers = []
    
    print(f"Scraping legacy teachers page: {url}...")
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

    print(f"Scraped {len(parsed_teachers)} teachers from legacy page.")

    # 2. Get DB faculty
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        res = await db.execute(select(Faculty))
        db_faculties = res.scalars().all()
        
        # 3. Match and download/save
        os.makedirs("public/uploads", exist_ok=True)
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for pt in parsed_teachers:
            cv_link = pt["cv_link"]
            if not cv_link:
                # No legacy CV link on the website, skip
                continue
                
            scraped_cleaned = pt["cleaned_name"]
            scraped_parts = scraped_cleaned.split(' ')
            scraped_fname = scraped_parts[0] if len(scraped_parts) > 0 else ""
            scraped_lname = scraped_parts[1] if len(scraped_parts) > 1 else ""
            
            match = None
            # Find matching faculty in DB
            for f in db_faculties:
                db_fname = clean_name(f.fname)
                db_lname = clean_name(f.lname)
                
                if scraped_fname == db_fname:
                    match = f
                    break
                elif scraped_fname in db_fname or db_fname in scraped_fname:
                    if scraped_lname and (scraped_lname in db_lname or db_lname in scraped_lname):
                        match = f
                        break
            
            if not match:
                print(f"WARN: Could not match legacy teacher '{pt['original_name']}' in DB. Skipping.")
                continue
                
            # Check if this faculty already has a CV in the database (we should not overwrite custom newly uploaded CVs)
            res_cv = await db.execute(select(FacultyCV).where(FacultyCV.user_id == match.id))
            faculty_cv = res_cv.scalars().first()
            
            if faculty_cv and faculty_cv.cv_file:
                print(f"INFO: Skipping ID {match.id} ({match.fname} {match.lname}) - already has CV: {faculty_cv.cv_file}")
                skip_count += 1
                continue
                
            # Download file from legacy URL
            absolute_cv_url = urllib.parse.urljoin("https://ww2.agi.nu.ac.th/nred/", cv_link)
            print(f"Downloading CV for ID {match.id} ({match.fname} {match.lname}) from {absolute_cv_url}...")
            
            try:
                dl_req = urllib.request.Request(absolute_cv_url, headers=headers)
                with urllib.request.urlopen(dl_req) as dl_res:
                    pdf_data = dl_res.read()
                    
                # Generate unique sanitized filename
                original_filename = os.path.basename(cv_link)
                sanitized_filename = re.sub(r'[^a-zA-Z0-9_\.-]', '', original_filename)
                unique_name = f"{uuid.uuid4().hex[:8]}_{sanitized_filename}"
                file_path = os.path.join("public/uploads", unique_name)
                
                # Write file locally
                with open(file_path, "wb") as pdf_file:
                    pdf_file.write(pdf_data)
                    
                db_path = f"/uploads/{unique_name}"
                
                # Save to database
                if faculty_cv:
                    faculty_cv.cv_file = db_path
                else:
                    db.add(FacultyCV(user_id=match.id, cv_file=db_path))
                    
                await db.flush()
                print(f"SUCCESS: Saved CV to {file_path} and added to DB path: {db_path}")
                success_count += 1
            except Exception as download_err:
                print(f"ERROR: Failed to download or save CV for {match.fname} {match.lname}: {download_err}")
                fail_count += 1
                
        # Commit database transaction
        await db.commit()
        print("\n--- Migration Summary ---")
        print(f"Successfully migrated: {success_count}")
        print(f"Skipped (already exist): {skip_count}")
        print(f"Failed downloads: {fail_count}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())

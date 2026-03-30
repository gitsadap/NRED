
import requests
from bs4 import BeautifulSoup
import psycopg2
import os

# PostgreSQL Config
import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

PREFIX_LIST = [
    "ศ.ดร.", "รศ.ดร.", "ผศ.ดร.", "ดร.", "อาจารย์", "อ.", 
    "ผู้ช่วยศาสตราจารย์", "รองศาสตราจารย์", "ศาสตราจารย์",
    "ผศ.", "รศ.", "ศ.", "นาย", "นาง", "นางสาว", "ว่าที่ร้อยตรี", "ร.ต."
]

MAJOR_MAPPING = {
    # 1: ภูมิศาสตร์ และภูมิสารสนเทศศาสตร์
    "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher1": "ภูมิศาสตร์และภูมิสารสนเทศศาสตร์",
    
    # 2: ทรัพยากรธรรมชาติและสิ่งแวดล้อม
    "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher2": "ทรัพยากรธรรมชาติและสิ่งแวดล้อม",
    
    # 3: วิทยาศาสตร์สิ่งแวดล้อม
    "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher3": "วิทยาศาสตร์สิ่งแวดล้อม"
}

def parse_name(full_name):
    # Determine prefix
    prefix = ""
    name_part = full_name
    
    # Sort prefix list by length descending to match longest first
    sorted_prefixes = sorted(PREFIX_LIST, key=len, reverse=True)
    
    for p in sorted_prefixes:
        if full_name.startswith(p):
            prefix = p
            name_part = full_name[len(p):].strip()
            break
            
    # Split fname/lname
    parts = name_part.split()
    fname = parts[0] if parts else ""
    lname = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    return prefix, fname, lname

def update_majors():
    print("Starting Major Update...")
    
    # Connect DB
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        cursor = conn.cursor()
        print("Connected to PostgreSQL.\n")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    total_updates = 0
    
    for url, major_name in MAJOR_MAPPING.items():
        print(f"Processing Major: {major_name} (URL: {url})")
        
        try:
            response = requests.get(url, verify=False)
            if 'charset=tis-620' in response.text.lower() or 'windows-874' in response.text.lower():
                 response.encoding = 'tis-620'
            elif 'charset=utf-8' in response.text.lower():
                 response.encoding = 'utf-8'
            else:
                 if response.encoding == 'ISO-8859-1':
                     response.encoding = 'tis-620'
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Using similar logic to scrape_personnel to find names
        outer_tables = soup.find_all('table', attrs={'border': '0', 'cellpadding': '5', 'cellspacing': '8'})
        
        personnel_found = 0
        
        for table in outer_tables:
            info_table = table.find('table', attrs={'border': '4'})
            if not info_table:
                continue
                
            rows = info_table.find_all('tr')
            full_name = ""
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 2:
                    continue
                label = cols[0].get_text(strip=True).replace(':', '').strip()
                if 'ชื่อ' in label and 'วิชา' not in label:
                    full_name = cols[1].get_text(strip=True)
                    break # Found name, break row loop
            
            if not full_name:
                continue
            
            prefix, fname, lname = parse_name(full_name)
            
            # Update DB with Major
            try:
                cursor.execute("""
                    UPDATE api.faculty 
                    SET major = %s 
                    WHERE fname = %s AND lname = %s
                """, (major_name, fname, lname))
                
                if cursor.rowcount > 0:
                    print(f"  ✓ Updated Major for: {fname} {lname}")
                    personnel_found += 1
                else:
                    print(f"  ⚠ Not Found in DB: {fname} {lname}")
                    
            except Exception as e:
                print(f"  ✗ Error updating {fname} {lname}: {e}")
                conn.rollback()
        
        conn.commit()
        print(f"Major '{major_name}' personnel updated: {personnel_found}\n")
        total_updates += personnel_found

    conn.close()
    print(f"Total Updates Complete: {total_updates}")

if __name__ == "__main__":
    update_majors()

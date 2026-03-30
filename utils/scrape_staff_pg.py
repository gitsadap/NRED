import requests
from bs4 import BeautifulSoup
import psycopg2
import os
import re

# PostgreSQL Config
import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

# Image Storage
IMAGE_DIR = 'static/images/personnel'

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_image(image_url, name):
    try:
        response = requests.get(image_url, stream=True, verify=False)
        if response.status_code == 200:
            ext = os.path.splitext(image_url)[1]
            if not ext:
                ext = '.jpg'
            safe_name = re.sub(r'[^\w\-\.\_ ]', '_', name)
            filename = safe_name + ext
            filepath = os.path.join(IMAGE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return f"/static/images/personnel/{filename}"
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
    return None

def scrape_staff():
    url = "https://ww2.agi.nu.ac.th/nred/personnel.php?view=staff"
    print(f"Fetching {url}...")
    
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
        print(f"Failed to fetch URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    outer_tables = soup.find_all('table', attrs={'border': '0', 'cellpadding': '5', 'cellspacing': '8'})
    print(f"Found {len(outer_tables)} personnel blocks.")
    
    ensure_dir(IMAGE_DIR)
    
    staff_data = []
    
    for tb in outer_tables:
        img_td = tb.find('td', width='30%')
        details_td = tb.find('td', width='69%')
        if not img_td or not details_td:
            continue
            
        img_tag = img_td.find('img')
        img_src = img_tag.get('src') if img_tag else ""
        if img_src and not img_src.startswith('http'):
            img_src = "https://ww2.agi.nu.ac.th/nred/" + img_src
            
        fname = ""
        lname = ""
        position = ""
        phone = ""
        email = ""
        
        trs = details_td.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) >= 2:
                label = tds[0].text.strip()
                val = tds[1].text.strip()
                if 'ชื่อ' in label:
                    name_parts = val.split()
                    if len(name_parts) >= 2:
                        fname = name_parts[0]
                        lname = " ".join(name_parts[1:])
                    else:
                        fname = val
                elif 'ตำแหน่ง' in label:
                    position = val
                elif 'เบอร์โทร' in label:
                    phone = val
                elif 'เมล์' in label:
                    email = val

        if "คุณ" in fname:
             fname = fname.replace("คุณ", "")
        if "นาย" in fname:
             fname = fname.replace("นาย", "")
        if "นางสาว" in fname:
             fname = fname.replace("นางสาว", "")
        if "นาง" in fname:
             fname = fname.replace("นาง", "")

        saved_img_path = None
        if img_src and 'No-Image' not in img_src:
            print(f"Downloading image for {fname}...")
            saved_img_path = download_image(img_src, fname)
            
        staff_data.append({
            'fname': fname,
            'lname': lname,
            'position': position,
            'phone': phone,
            'email': email,
            'image': saved_img_path
        })
        
    if not staff_data:
        print("No staff found!")
        return
        
    try:
        conn = psycopg2.connect(host=PG_HOST, user=PG_USER, password=PG_PASS, dbname=PG_DB)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if they exist to avoid duplicates
        cur.execute("SELECT fname, lname FROM api.faculty;")
        existing = set((r[0], r[1]) for r in cur.fetchall())
        
        inserted = 0
        for s in staff_data:
            if (s['fname'], s['lname']) in existing:
                print(f"Skipping {s['fname']} (already exists)")
                continue
                
            cur.execute("""
                INSERT INTO api.faculty (fname, lname, position, phone, email, image, major)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (s['fname'], s['lname'], s['position'], s['phone'], s['email'], s['image'], 'บุคลากรสายสนับสนุน'))
            inserted += 1
            print(f"Inserted: {s['fname']}")
            
        print(f"Successfully inserted {inserted} staff members into api.faculty")
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    scrape_staff()

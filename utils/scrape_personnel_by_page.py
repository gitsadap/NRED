
import requests
from bs4 import BeautifulSoup
import psycopg2
import os
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

PREFIX_LIST = [
    "ศ.ดร.", "รศ.ดร.", "ผศ.ดร.", "ดร.", "อาจารย์", "อ.", 
    "ผู้ช่วยศาสตราจารย์", "รองศาสตราจารย์", "ศาสตราจารย์",
    "ผศ.", "รศ.", "ศ.", "นาย", "นาง", "นางสาว", "ว่าที่ร้อยตรี", "ร.ต."
]

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_image(image_url, name):
    try:
        response = requests.get(image_url, stream=True, verify=False, timeout=10)
        if response.status_code == 200:
            ext = os.path.splitext(image_url)[1]
            if not ext or len(ext) > 5:
                ext = '.jpg'
            safe_name = re.sub(r'[^\w\-_\. ]', '_', name)
            filename = safe_name + ext
            filepath = os.path.join(IMAGE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            # Return web accessible path
            return f"/static/images/personnel/{filename}"
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
    return None

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

def scrape_personnel_page():
    url = "https://www.agi.nu.ac.th/?page_id=3949"
    print(f"Fetching {url}...")
    
    try:
        response = requests.get(url, verify=False, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    except Exception as e:
        print(f"Failed to fetch URL: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Based on research, personnel info is in div.kc-team
    team_members = soup.find_all('div', class_='kc-team')
    print(f"Found {len(team_members)} personnel blocks.")
    
    ensure_dir(IMAGE_DIR)
    
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        cursor = conn.cursor()
        print("Connected to PostgreSQL.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    count_update = 0
    count_insert = 0
    
    for member in team_members:
        # 1. Parse Info
        name_div = member.find('div', class_='content-title')
        full_name = name_div.get_text(strip=True) if name_div else ""
        
        if not full_name:
            continue

        prefix, fname, lname = parse_name(full_name)
        
        position_div = member.find('div', class_='content-subtitle')
        position = position_div.get_text(strip=True) if position_div else ""
        
        desc_div = member.find('div', class_='content-desc')
        email = ""
        phone = ""
        
        if desc_div:
            desc_text = desc_div.get_text()
            # Extract email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', desc_text)
            if email_match:
                email = email_match.group(0)
            
            # Extract phone
            phone_match = re.search(r'0\d{2}-\d{6}', desc_text)
            if phone_match:
                phone = phone_match.group(0)

        # Determine NU Account / Filename base
        nu_account = ""
        if email:
            nu_account = email.split('@')[0]
        else:
            # Fallback if no email, though user requested NU account specifically.
            # We'll stick to name-based fallback if email is missing, or log warning.
            # But let's try to ensure we have it or normalize name.
            print(f"Warning: No email found for {fname} {lname}, using name for file.")
            nu_account = f"{fname}_{lname}"

        # 2. Parse Image
        img_tag = member.find('img')
        img_src = None
        local_image_path = None
        
        if img_tag and 'src' in img_tag.attrs:
            img_src = img_tag['src']
            if img_src:
                local_image_path = download_image(img_src, nu_account)

        print(f"Processing: {prefix} {fname} {lname} -> {nu_account}")

        # 3. Update DB
        try:
             # Find by fname/lname
             cursor.execute("SELECT id FROM api.faculty WHERE fname = %s AND lname = %s", (fname, lname))
             existing = cursor.fetchone()
             
             if existing:
                 pid = existing[0]
                 update_fields = []
                 params = []
                 
                 update_fields.append("prefix = %s")
                 params.append(prefix)
                 
                 update_fields.append("position = %s")
                 params.append(position)

                 if local_image_path:
                     update_fields.append("image = %s")
                     params.append(local_image_path)
                     
                 if email:
                     update_fields.append("email = %s")
                     params.append(email)
                 
                 if phone:
                     update_fields.append("phone = %s")
                     params.append(phone)
                     
                 update_fields.append("updated_at = NOW()")
                     
                 if update_fields:
                     sql = f"UPDATE api.faculty SET {', '.join(update_fields)} WHERE id = %s"
                     params.append(pid)
                     cursor.execute(sql, tuple(params))
                     count_update += 1
                     conn.commit()
             else:
                 cols = ["prefix", "fname", "lname", "position"]
                 vals = [prefix, fname, lname, position]
                 placeholders = ["%s", "%s", "%s", "%s"]
                 
                 if email:
                     cols.append("email")
                     vals.append(email)
                     placeholders.append("%s")
                 
                 if local_image_path:
                     cols.append("image")
                     vals.append(local_image_path)
                     placeholders.append("%s")
                     
                 if phone:
                    cols.append("phone")
                    vals.append(phone)
                    placeholders.append("%s")
                
                 cols.append("updated_at")
                 vals.append("NOW()") # This won't work as param, need to handle separately or use current_timestamp
                 
                 # Fix for updated_at in INSERT
                 # Remove "NOW()" from vals and append to placeholders directly in SQL construction
                 vals.pop() # Remove "NOW()" string
                 
                 sql = f"INSERT INTO api.faculty ({', '.join(cols)}) VALUES ({', '.join(placeholders)}, NOW())"
                 cursor.execute(sql, tuple(vals))
                 count_insert += 1
                 conn.commit()

        except Exception as e:
            print(f"DB Error for {fname} {lname}: {e}")
            conn.rollback()

    conn.close()
    print(f"Done. Updated: {count_update}, Inserted: {count_insert}")

if __name__ == "__main__":
    scrape_personnel_page()

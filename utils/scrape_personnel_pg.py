
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
        response = requests.get(image_url, stream=True, verify=False)
        if response.status_code == 200:
            ext = os.path.splitext(image_url)[1]
            if not ext:
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

import json

def get_table_columns_info(cursor, table_name, schema='api'):
    """Returns a dictionary of {column_name: data_type}"""
    cursor.execute("""
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s
    """, (schema, table_name))
    return {row[0]: {'data_type': row[1], 'udt_name': row[2]} for row in cursor.fetchall()}

def scrape_personnel_pg():
    url = "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher"
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
    
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        cursor = conn.cursor()
        print("Connected to PostgreSQL.")
        
        # Check Columns and Types
        cols_info = get_table_columns_info(cursor, 'faculty', 'api')
        columns = list(cols_info.keys())
        print(f"Table columns: {columns}")
        
        has_expertise = 'expertise' in columns
        expertise_type = cols_info['expertise']['udt_name'] if has_expertise else None
        print(f"Expertise Column: {has_expertise} (Type: {expertise_type})")

        has_image = 'image' in columns
        has_email = 'email' in columns
        has_updated_at = 'updated_at' in columns
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    count_update = 0
    count_insert = 0
    
    for table in outer_tables:
        person = {}

        # 1. Parse Image
        img_tag = table.find('img')
        if img_tag and 'src' in img_tag.attrs:
            img_src = img_tag['src']
            if not img_src.startswith('http'):
                img_src = f"https://ww2.agi.nu.ac.th/nred/{img_src}"
            person['image_url'] = img_src
        else:
            person['image_url'] = None

        # 2. Parse Info
        info_table = table.find('table', attrs={'border': '4'})
        if not info_table:
            continue
            
        rows = info_table.find_all('tr')
        full_name = ""
        position = ""
        email = ""
        expertise_list = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            
            label = cols[0].get_text(strip=True).replace(':', '').strip()
            # value = cols[1].get_text(strip=True) # Don't use simple get_text for expertise
            
            if 'ชื่อ' in label and 'วิชา' not in label:
                full_name = cols[1].get_text(strip=True)
            elif 'ตำแหน่ง' in label:
                position = cols[1].get_text(strip=True)
            elif 'อีเมล' in label:
                email = cols[1].get_text(strip=True)
            elif 'ความเชี่ยวชาญ' in label:
                # Advanced parsing for expertise array
                # The text uses '»' as bullets and <br> for newlines. 
                # We replace '»' with a unique splitter to separate items easily.
                raw_text = cols[1].get_text(separator='|', strip=True)
                
                # Method 1: Split by the bullet character '»'
                if '»' in raw_text:
                    parts = raw_text.split('»')
                else:
                    # Method 2: Fallback to newline/pipe splitting if no bullets found
                    parts = raw_text.split('|')

                # Clean up items
                for part in parts:
                    clean_item = part.replace('|', ' ').strip()
                    # Filter out noise and empty strings
                    if clean_item and len(clean_item) > 2 and 'cv link file' not in clean_item.lower():
                         expertise_list.append(clean_item)

        if not full_name:
            continue
            
        # Prepare Expertise Data
        final_expertise = None
        if has_expertise:
            if expertise_type and expertise_type.startswith('_'): # Array types in PG usually start with underscore e.g. _text
                 final_expertise = expertise_list
            elif expertise_type in ['json', 'jsonb']:
                 final_expertise = json.dumps(expertise_list, ensure_ascii=False)
            else:
                 # Default to JSON string for TEXT columns to simulate array
                 final_expertise = json.dumps(expertise_list, ensure_ascii=False)

        # Parse Name Parts
        prefix, fname, lname = parse_name(full_name)
        print(f"Processing: {prefix} {fname} {lname} | Exp: {len(expertise_list)} items")
        
        # Download Image
        local_image_path = None
        if person.get('image_url'):
            local_image_path = download_image(person['image_url'], f"{fname}_{lname}")

        # Check existing
        cursor.execute("SELECT id FROM api.faculty WHERE fname = %s AND lname = %s", (fname, lname))
        existing = cursor.fetchone()
        
        try:
            if existing:
                # UPDATE
                pid = existing[0]
                update_fields = []
                params = []
                
                update_fields.append("prefix = %s")
                params.append(prefix)
                
                update_fields.append("position = %s")
                params.append(position)
                
                if has_email:
                    update_fields.append("email = %s")
                    params.append(email)
                
                if has_expertise:
                    update_fields.append("expertise = %s")
                    params.append(final_expertise)
                
                if has_image and local_image_path:
                    update_fields.append("image = %s")
                    params.append(local_image_path)
                
                if has_updated_at:
                    update_fields.append("updated_at = NOW()")
                    
                sql = f"UPDATE api.faculty SET {', '.join(update_fields)} WHERE id = %s"
                params.append(pid)
                
                cursor.execute(sql, tuple(params))
                count_update += 1
                
            else:
                # INSERT
                fields = ["prefix", "fname", "lname", "position"]
                placeholders = ["%s", "%s", "%s", "%s"]
                params = [prefix, fname, lname, position]
                
                if has_email:
                    fields.append("email")
                    placeholders.append("%s")
                    params.append(email)
                
                if has_expertise:
                    fields.append("expertise")
                    placeholders.append("%s")
                    params.append(final_expertise)
                
                if has_image and local_image_path:
                    fields.append("image")
                    placeholders.append("%s")
                    params.append(local_image_path)
                    
                if has_updated_at:
                    fields.append("updated_at")
                    placeholders.append("NOW()")
                
                sql = f"INSERT INTO api.faculty ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(sql, tuple(params))
                count_insert += 1

            conn.commit()

        except Exception as e:
            print(f"DB Error for {fname} {lname}: {e}")
            conn.rollback()

    print(f"Sync complete. Updated: {count_update}, Inserted: {count_insert}")
    conn.close()

if __name__ == "__main__":
    scrape_personnel_pg()

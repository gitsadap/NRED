
import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import re

# Database Path
DB_PATH = 'data/cms.db'
IMAGE_DIR = 'static/images/personnel'

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_image(image_url, name):
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            ext = os.path.splitext(image_url)[1]
            if not ext:
                ext = '.jpg'
            # Sanitize filename
            safe_name = re.sub(r'[^\w\-_\. ]', '_', name)
            filename = safe_name + ext
            filepath = os.path.join(IMAGE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filepath
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
    return None

def scrape_personnel():
    url = "https://ww2.agi.nu.ac.th/nred/personnel.php?view=teacher"
    print(f"Fetching {url}...")
    
    try:
        response = requests.get(url, verify=False)  # verify=False for simplicity with https sites sometimes having ssl issues
        response.encoding = 'utf-8' # Force UTF-8 if needed, or adjust based on response headers but typically Thai sites might use TIS-620. Let's see.
        
        # Check encoding from meta tag or header if possible, but let's assume TIS-620 or UTF-8. 
        # Actually requests often auto-detects, but if it fails for Thai, try TIS-620.
        if 'charset=tis-620' in response.text.lower() or 'windows-874' in response.text.lower():
             response.encoding = 'tis-620'
        elif 'charset=utf-8' in response.text.lower():
             response.encoding = 'utf-8'
        else:
            # Fallback for Thai government sites often being TIS-620
            # If requests detected ISO-8859-1 (default), force TIS-620 or UTF-8
            if response.encoding == 'ISO-8859-1':
                 # Let's try TIS-620 first as it's common for older PHP sites
                 response.encoding = 'tis-620'

    except Exception as e:
        print(f"Failed to fetch URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Locate personnel tables
    # Structure seems to be nested tables. Outer table has rows with image + info table.
    # Looking at HTML structure: 
    # Each person block is within a table structure. We can find image and info table.
    
    # Broad strategy: Find all tables that have "border=4". In the provided HTML, the info table has border="4". 
    # Or find `strong` tags with "ชื่อ :" text.
    
    people = []
    
    # Iterate through potential personnel blocks
    # The structure provided shows consistent pattern:
    # Outer table with 2 columns: Image (24%) and Info (76%)
    
    outer_tables = soup.find_all('table', attrs={'border': '0', 'cellpadding': '5', 'cellspacing': '8'})
    
    print(f"Found {len(outer_tables)} personnel blocks.")
    
    for table in outer_tables:
        person = {}
        
        # 1. Image
        img_tag = table.find('img')
        if img_tag and 'src' in img_tag.attrs:
            img_src = img_tag['src']
            if not img_src.startswith('http'):
                img_src = f"https://ww2.agi.nu.ac.th/nred/{img_src}"
            person['image_url'] = img_src
        else:
            person['image_url'] = None

        # 2. Info Table (the one with border=4)
        info_table = table.find('table', attrs={'border': '4'})
        if not info_table:
            continue
            
        rows = info_table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
                
            label = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            
            # Clean up label (remove colon)
            label = label.replace(':', '').strip()
            
            if 'ชื่อ' in label and 'วิชา' not in label: # Avoid 'รายชื่อวิชา' if any
                person['name'] = value
            elif 'ตำแหน่ง' in label:
                person['position'] = value
            elif 'อีเมล' in label:
                person['email'] = value
            elif 'ความเชี่ยวชาญ' in label:
                # Capture text but also check for <br> or <li> for formatting if needed, 
                # but get_text is usually fine.
                # However, the provided HTML shows structured data with bullets.
                # Let's try to keep it readable.
                expertise_text = cols[1].get_text(separator='\n', strip=True) 
                # Remove bullets like »
                expertise_text = expertise_text.replace('»', '-').strip()
                person['expertise'] = expertise_text
        
        if 'name' in person:
            people.append(person)
            print(f"Parsed: {person['name']}")

    # Update Database
    if not people:
        print("No personnel found to update.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    ensure_dir(IMAGE_DIR)
    
    count_new = 0
    count_update = 0
    
    for p in people:
        name = p.get('name', 'Unknown')
        position = p.get('position', '')
        email = p.get('email', '')
        expertise = p.get('expertise', '')
        image_url = p.get('image_url')
        
        # Download image
        local_image_path = None
        if image_url:
            local_image_path = download_image(image_url, name)
            if local_image_path:
                # Store relative path for web access
                # Remove static/ prefix if your app serves static files from root or keep it
                # Usually in HTML: src="/static/images/personnel/..."
                # Storing: "static/images/personnel/..."
                # Let's store the path relative to project root or accessible path
                 local_image_path = "/" + local_image_path
        
        # Check if exists
        cursor.execute("SELECT id, image FROM staff WHERE name = ?", (name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update
            # Use existing image if download failed or new one is None? 
            # Or always overwrite? Let's overwrite if we got a new one.
            db_image = local_image_path if local_image_path else existing[1]
            
            cursor.execute("""
                UPDATE staff 
                SET position=?, email=?, expertise=?, image=?, type='faculty'
                WHERE id=?
            """, (position, email, expertise, db_image, existing[0]))
            count_update += 1
        else:
            # Insert
            cursor.execute("""
                INSERT INTO staff (name, position, email, expertise, image, type, created_at)
                VALUES (?, ?, ?, ?, ?, 'faculty', CURRENT_TIMESTAMP)
            """, (name, position, email, expertise, local_image_path))
            count_new += 1
            
    conn.commit()
    conn.close()
    
    print(f"Done! {count_new} new records, {count_update} updated records.")

if __name__ == "__main__":
    scrape_personnel()

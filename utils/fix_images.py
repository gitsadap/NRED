import os
import psycopg2

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

def fix_images():
    conn = psycopg2.connect(host=PG_HOST, user=PG_USER, password=PG_PASS, dbname=PG_DB)
    conn.autocommit = True
    cur = conn.cursor()

    image_dir = "static/images/personnel"
    images = os.listdir(image_dir)
    image_map = {f.split('.')[0].lower(): f for f in images if f != '.DS_Store'}

    cur.execute("SELECT id, email, fname_en, lname_en FROM api.faculty;")
    rows = cur.fetchall()

    updated = 0
    for row in rows:
        uid, email, fname_en, lname_en = row
        matched_image = None
        
        # 1. Try to match by email prefix
        emails = [e.strip().lower() for e in (email or "").split(",")]
        for em in emails:
            prefix = em.split('@')[0]
            if prefix in image_map:
                matched_image = image_map[prefix]
                break
        
        # 2. Try to match by fname_en + first letter of lname_en
        if not matched_image and fname_en and lname_en:
            composed = (fname_en + lname_en[0]).lower()
            if composed in image_map:
                matched_image = image_map[composed]
                
        # 3. Try partial matches (e.g. pattana, pongsakn)
        if not matched_image and fname_en:
            fn = fname_en.lower()
            for key, filename in image_map.items():
                if key.startswith(fn) or fn.startswith(key):
                    matched_image = filename
                    break

        if matched_image:
            img_path = f"/static/images/personnel/{matched_image}"
            cur.execute("UPDATE api.faculty SET image = %s WHERE id = %s", (img_path, uid))
            updated += 1
            print(f"Updated User ID {uid} -> {img_path}")

    print(f"Total updated: {updated}")
    conn.close()

if __name__ == '__main__':
    fix_images()

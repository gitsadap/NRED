import json
import psycopg2

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

def restore_eng_names():
    with open('faculty_en.json', 'r') as f:
        data = json.load(f)

    conn = psycopg2.connect(host=PG_HOST, user=PG_USER, password=PG_PASS, dbname=PG_DB)
    conn.autocommit = True
    cur = conn.cursor()

    count = 0
    for entry in data:
        en_full = entry['name_en']
        uid = entry['id']
        
        parts = en_full.split()
        if parts and parts[0] in ['Dr.', 'Mr.', 'Ms.']:
            parts.pop(0)
        
        fname_en = parts[0] if parts else ""
        lname_en = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        cur.execute("UPDATE api.faculty SET fname_en = %s, lname_en = %s WHERE id = %s", (fname_en, lname_en, uid))
        if cur.rowcount > 0:
            count += 1
            print(f"Updated user {uid} with {fname_en} {lname_en}")

    print(f"Done. Updated {count} users.")
    conn.close()

if __name__ == '__main__':
    restore_eng_names()

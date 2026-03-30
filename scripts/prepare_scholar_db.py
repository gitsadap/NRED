import psycopg2
import json

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

def check_db_and_alter():
    conn = psycopg2.connect(
        host=PG_HOST,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    cursor = conn.cursor()
    print("Connected to DB.")
    
    # Check if scholar_data column exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'api' AND table_name = 'faculty' AND column_name = 'scholar_data';
    """)
    if not cursor.fetchone():
        print("Adding scholar_data JSONB column...")
        cursor.execute("ALTER TABLE api.faculty ADD COLUMN scholar_data JSONB;")
        conn.commit()
    else:
        print("scholar_data column already exists.")
        
    # Fetch faculty names
    cursor.execute("SELECT id, fname_en, lname_en, lname FROM api.faculty;")
    rows = cursor.fetchall()
    
    faculty_list = []
    for row in rows:
        fid, fname_en, lname_en, lname_th = row
        print(f"ID: {fid} | {fname_en} {lname_en} (TH: {lname_th})")
        faculty_list.append({"id": fid, "lname_en": lname_en, "lname_th": lname_th})
        
    conn.close()

if __name__ == "__main__":
    check_db_and_alter()

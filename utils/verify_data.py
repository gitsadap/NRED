
import psycopg2
import json

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

try:
    conn = psycopg2.connect(
        host=PG_HOST,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    cursor = conn.cursor()
    
    print("--- Verifying Faculty Data ---")
    cursor.execute("""
        SELECT prefix, fname, lname, image, updated_at 
        FROM api.faculty 
        WHERE updated_at IS NOT NULL 
        ORDER BY updated_at DESC 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"{row[0]} {row[1]} {row[2]} | Img: {row[3]} | Updated: {row[4]}")
        
    conn.close()

except Exception as e:
    print(e)

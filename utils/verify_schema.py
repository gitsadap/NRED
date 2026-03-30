
import psycopg2

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
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'api' AND table_name = 'faculty'
    """)
    columns = cursor.fetchall()
    print("Columns in api.faculty:")
    for col in columns:
        print(col)
    conn.close()
except Exception as e:
    print(e)

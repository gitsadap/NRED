
import psycopg2

# PostgreSQL Config
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
    
    print(f"Connecting to database '{PG_DB}' on '{PG_HOST}'...")
    print("Checking table 'api.faculty'...\n")
    
    # Check count
    cursor.execute("SELECT COUNT(*) FROM api.faculty")
    count = cursor.fetchone()[0]
    print(f"Total Rows: {count}")
    
    # Check sample data
    cursor.execute("""
        SELECT fname, lname, position, expertise 
        FROM api.faculty 
        ORDER BY updated_at DESC 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    
    print("\n--- Recent Updates (Top 5) ---")
    for row in rows:
        print(f"Name: {row[0]} {row[1]}")
        print(f"Position: {row[2]}")
        print(f"Expertise: {row[3]}")
        print("-" * 30)

    conn.close()

except Exception as e:
    print(f"Error: {e}")

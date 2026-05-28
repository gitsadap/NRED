
import pymysql
import json
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_metadata():
    host = os.getenv("MYSQL_HOST", "").strip()
    user = os.getenv("MYSQL_USER", "").strip()
    pw = os.getenv("MYSQL_PASSWORD", "").strip()
    dbname = os.getenv("MYSQL_DB", "db_user").strip()
    if not host or not user or not pw:
        raise RuntimeError("Missing MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD environment variables")

    print(f"Connecting to {host}...")
    try:
        conn = pymysql.connect(host=host, user=user, password=pw, db=dbname, charset='utf8', cursorclass=pymysql.cursors.DictCursor, connect_timeout=5)
        print("Connected successfully!")
        
        with conn.cursor() as cursor:
            # 1. Fetch Departments
            print("\n--- Departments ---")
            cursor.execute("SELECT * FROM department")
            depts = cursor.fetchall()
            for d in depts:
                print(d)

            # 2. Fetch Staff Types (if table exists)
            # print("\n--- Staff Types ---")
            
            # 3. Fetch Position Types (if table exists)
            # print("\n--- Positions (First 10) ---")
                
        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    inspect_metadata()

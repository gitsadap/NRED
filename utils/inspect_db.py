
import pymysql
import json
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_db():
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
            # 1. Get Tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("\n--- Tables ---")
            for t in tables:
                print(list(t.values())[0])
            
            # 2. Get Columns for lookup tables
            target_tables = ['department', 'position', 'prefix', 'academic_position', 'user']
            
            for table in target_tables:
                print(f"\n--- Columns in '{table}' ---")
                try:
                    cursor.execute(f"SHOW COLUMNS FROM {table}")
                    columns = cursor.fetchall()
                    for c in columns:
                        print(f"{c['Field']} ({c['Type']})")
                    
                    # Dump 1 row sample
                    print(f"--- Sample Data from '{table}' ---")
                    cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                    row = cursor.fetchone()
                    print(json.dumps(row, default=str, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(f"Error inspecting {table}: {e}")
            
            return
                
        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    inspect_db()

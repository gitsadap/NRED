
import pymysql
import json

def inspect_db():
    host = "10.10.58.16"
    user = "gitsadap"
    pw = "it[[{ko-hv,^]8ItgdK9i"
    dbname = "db_user"

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


import pymysql
import json

def inspect_metadata():
    host = "10.10.58.16"
    user = "gitsadap"
    pw = "it[[{ko-hv,^]8ItgdK9i"
    dbname = "db_user"

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

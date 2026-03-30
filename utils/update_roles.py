
import psycopg2

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

def update_roles():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to PostgreSQL.")

        # 1. Add Columns
        columns_to_add = {
            'is_program_chair': 'BOOLEAN DEFAULT FALSE',
            'is_expert': 'BOOLEAN DEFAULT FALSE'
        }
        
        for col, dtype in columns_to_add.items():
            cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema='api' AND table_name='faculty' AND column_name='{col}'
            """)
            if cursor.fetchone():
                print(f"Column '{col}' already exists.")
            else:
                cursor.execute(f"ALTER TABLE api.faculty ADD COLUMN {col} {dtype}")
                print(f"✅ Column '{col}' added successfully.")

        # 2. Update Experts (Pattana & Pongsak)
        # Reset everyone to False first? No, maybe cumulative.
        
        experts = ['พัฒนา', 'พงศ์ศักดิ์']
        
        for name in experts:
            # Check if exists
            cursor.execute("SELECT id, fname, lname FROM api.faculty WHERE fname LIKE %s", (f"%{name}%",))
            results = cursor.fetchall()
            
            if results:
                for row in results:
                    pid, fname, lname = row
                    cursor.execute("UPDATE api.faculty SET is_expert = TRUE WHERE id = %s", (pid,))
                    print(f"  ✓ Set '{fname} {lname}' as Expert.")
            else:
                print(f"  ⚠ Person named '{name}' not found in database.")
                
                # If Pongsak not found, try inserting him?
                if name == 'พงศ์ศักดิ์':
                     print("    (Note: 'พงศ์ศักดิ์' might need to be added manually if not in the scrapable lists)")

        conn.close()
        print("\nUpdate Complete.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_roles()

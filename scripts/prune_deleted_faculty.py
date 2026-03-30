import psycopg2

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"

def main():
    try:
        conn = psycopg2.connect(host=PG_HOST, database=PG_DB, user=PG_USER, password=PG_PASS)
        cursor = conn.cursor()
        print("Connected to PostgreSQL.")
        
        # Get active staff names
        cursor.execute("SELECT name FROM staff")
        active_staff = [s[0].strip() for s in cursor.fetchall()]
        
        # Get all faculty in api.faculty
        cursor.execute("SELECT id, fname, lname FROM api.faculty")
        faculty_list = cursor.fetchall()
        
        deleted_count = 0
        for fid, fname, lname in faculty_list:
            # Reconstruct the name as stored in staff table (typically "Firstname Lastname")
            # We do a loose check because Thai names might have titles
            name_match = False
            for staff_name in active_staff:
                if fname in staff_name and lname in staff_name:
                    name_match = True
                    break
            
            if not name_match:
                print(f"Orphaned record detected: {fname} {lname} (ID: {fid}) - NOT FOUND in active CMS staff.")
                cursor.execute("DELETE FROM api.faculty WHERE id = %s", (fid,))
                deleted_count += 1
                
        conn.commit()
        print(f"\\nSuccessfully pruned {deleted_count} deleted faculty members from the research cache.")
        
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()

import psycopg2
import json
import requests
import time

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"
SERP_API_KEY = "27c618618b2c4d420a2b4a2bdf7efbf8754e67f82e3b2154a1ed9f3a354e2476"

def fetch_organic_results(query):
    url = f"https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "hl": "en",
        "q": query,
        "api_key": SERP_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("organic_results", [])
    except Exception as e:
        print(f"    -> Error parsing {query}: {e}")
        return []

def main():
    try:
        conn = psycopg2.connect(host=PG_HOST, database=PG_DB, user=PG_USER, password=PG_PASS)
        cursor = conn.cursor()
        
        # Get missing folks
        cursor.execute("SELECT id, fname, lname, fname_en, lname_en FROM api.faculty WHERE scholar_data IS NULL ORDER BY id ASC")
        missing_faculty = cursor.fetchall()
        print(f"Fetching organic fallback results for {len(missing_faculty)} missing profiles...")
        
        for fid, fname_th, lname_th, fname_en, lname_en in missing_faculty:
            fullname_th = f"{fname_th} {lname_th}".strip()
            fullname_en = f"{fname_en} {lname_en}".strip()
            print(f"\n[{fid}] Fallback Fetching: {fullname_en} ({fullname_th})")
            
            # 1st try: English
            query = f"{fullname_en} Naresuan University"
            print(f"  -> Organic Search: '{query}'")
            results = fetch_organic_results(query)
            time.sleep(1)
            
            # 2nd try: Thai
            if not results:
                query_th = f"{fullname_th} Naresuan University"
                print(f"  -> English returned 0 results. Trying Thai: '{query_th}'")
                results = fetch_organic_results(query_th)
                time.sleep(1)
                
            if results:
                print(f"  -> SUCCESS! Found {len(results)} raw organic publications.")
                cursor.execute("""
                    UPDATE api.faculty 
                    SET scholar_data = %s, cited = %s
                    WHERE id = %s
                """, (json.dumps(results, ensure_ascii=False), json.dumps({}, ensure_ascii=False), fid))
                conn.commit()
            else:
                print(f"  -> Completely FAILED to find any organic results.")

    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

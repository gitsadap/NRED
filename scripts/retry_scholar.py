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

def retry_missing_scholar():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        cursor = conn.cursor()
        print("Connected to PostgreSQL for retrying missing profiles.")
        
        # Fetch faculty with empty or null scholar data
        cursor.execute("""
            SELECT id, fname, lname, fname_en, lname_en 
            FROM api.faculty 
            WHERE scholar_data IS NULL OR jsonb_array_length(scholar_data) = 0
        """)
        missing_faculty = cursor.fetchall()
        
        print(f"Found {len(missing_faculty)} missing faculty members to retry.")
        
        total_updated = 0
        
        for fid, fname_th, lname_th, fname_en, lname_en in missing_faculty:
            # We will try a few query variations
            queries_to_try = [
                f"{fname_th} {lname_th} Naresuan University", # Full Thai Name + Eng Uni
                f"{fname_en} {lname_en} Naresuan University", # Full Eng Name + Eng Uni
                f"{fname_th} {lname_th} มหาวิทยาลัยนเรศวร",   # Full Thai Name + Thai Uni
            ]
            
            found = False
            
            for query in queries_to_try:
                print(f"[{fid}] Querying variant: {query}...")
                
                url = f"https://serpapi.com/search.json"
                params = {
                    "engine": "google_scholar",
                    "hl": "en",
                    "q": query,
                    "api_key": SERP_API_KEY
                }
                
                try:
                    response = requests.get(url, params=params)
                    data = response.json()
                    organic_results = data.get("organic_results", [])
                    
                    if organic_results:
                        print(f"  -> SUCCESS! Found {len(organic_results)} organic results for {fname_th}.")
                        
                        cursor.execute(
                            "UPDATE api.faculty SET scholar_data = %s WHERE id = %s",
                            (json.dumps(organic_results, ensure_ascii=False), fid)
                        )
                        conn.commit()
                        total_updated += 1
                        found = True
                        break # Stop trying other variants for this person
                    else:
                        print(f"  -> No results for this variant.")
                        
                except Exception as e:
                    print(f"  -> Error API requesting: {e}")
                    
                time.sleep(1) # rate limit
            
            if not found:
                print(f"❌ Completely failed to find {fname_th} {lname_th} after all variants.")
                
        print(f"\nCompleted retry! Successfully recovered {total_updated} records.")
            
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    retry_missing_scholar()

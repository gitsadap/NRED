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

def fetch_author_id(query):
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
        data = response.json()
        
        profiles = data.get("profiles", {}).get("authors", [])
        if profiles and len(profiles) > 0:
            return profiles[0].get("author_id")
            
        organic_results = data.get("organic_results", [])
        for pub in organic_results:
            pub_info = pub.get("publication_info", {})
            authors = pub_info.get("authors", [])
            for author in authors:
                if "author_id" in author:
                    return author["author_id"]
    except Exception as e:
        print(f"    -> Error finding profile for {query}: {e}")
    return None

def fetch_author_data(author_id):
    url = f"https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar_author",
        "hl": "en",
        "author_id": author_id,
        "api_key": SERP_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    -> Error fetching author dataset for {author_id}: {e}")
        return None

def main():
    try:
        conn = psycopg2.connect(host=PG_HOST, database=PG_DB, user=PG_USER, password=PG_PASS)
        cursor = conn.cursor()
        print("Connected to PostgreSQL.")
        
        # Target specific names
        target_names = ["Tanyaluck Chansombat", "Noulkamol Arpornpong", "Nichakorn Khondee"]
        
        for name in target_names:
            print(f"\nProcessing: {name}")
            
            # Fetch ID to get the primary key in our DB (using ILIKE for partial matches just in case)
            first_name = name.split()[0]
            cursor.execute("SELECT id, fname_en, lname_en, fname, lname FROM api.faculty WHERE fname_en ILIKE %s", (f"%{first_name}%",))
            row = cursor.fetchone()
            
            if not row:
                print(f"  -> Could not find {name} in the local database api.faculty table.")
                continue
                
            fid, db_fname_en, db_lname_en, fname_th, lname_th = row
            fullname_th = f"{fname_th} {lname_th}".strip()
            print(f"  -> Found in DB: ID={fid}, English={db_fname_en} {db_lname_en}, Thai={fullname_th}")
            
            # Try finding author ID
            author_id = None
            
            # Try English
            eng_query = f"{name} Naresuan University"
            print(f"  -> Fetching Scholar ID via: '{eng_query}'")
            author_id = fetch_author_id(eng_query)
            
            # Try Thai if English fails
            if not author_id:
                th_query = f"{fullname_th} Naresuan University"
                print(f"  -> English failed. Fetching via: '{th_query}'")
                author_id = fetch_author_id(th_query)
                time.sleep(1)
                
            if author_id:
                print(f"  -> SUCCESS! Found Scholar ID: {author_id}")
                cursor.execute("UPDATE api.faculty SET scholar_id = %s WHERE id = %s", (author_id, fid))
                conn.commit()
                
                print(f"  -> Fetching robust articles & citations using ID: {author_id}...")
                author_data = fetch_author_data(author_id)
                time.sleep(1)
                
                if author_data:
                    articles = author_data.get("articles", [])
                    cited_by = author_data.get("cited_by", {})
                    print(f"  -> Retrieved {len(articles)} articles and citation metrics.")
                    
                    cursor.execute("""
                        UPDATE api.faculty 
                        SET scholar_data = %s, cited = %s
                        WHERE id = %s
                    """, (json.dumps(articles, ensure_ascii=False), json.dumps(cited_by, ensure_ascii=False), fid))
                    conn.commit()
                else:
                    print(f"  -> FAILED to fetch detailed author data.")
            else:
                print(f"  -> FAILED to find Scholar ID.")

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

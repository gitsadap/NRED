import psycopg2
import json
import requests
import time
import re

import os
from dotenv import load_dotenv
load_dotenv()
PG_HOST = os.getenv("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com")
PG_USER = "agi"
PG_PASS = os.getenv("DB_PASSWORD", "")
PG_DB   = "nred"
SERP_API_KEY = "27c618618b2c4d420a2b4a2bdf7efbf8754e67f82e3b2154a1ed9f3a354e2476"

def normalize_name(name):
    if not name:
        return ""
    # Remove titles, punctuation, and extra spaces, convert to lowercase
    name = name.lower()
    for title in ['dr.', 'prof.', 'ผศ.', 'รศ.', 'ศ.', 'ดร.', 'นาย', 'นาง', 'นางสาว']:
        name = name.replace(title, '')
    name = re.sub(r'[^a-z0-9ก-๙\s]', '', name)
    return " ".join(name.split())

def check_name_match(api_name, db_fname_en, db_lname_en, db_fname_th, db_lname_th):
    api_norm = normalize_name(api_name)
    
    # Extract parts
    fname_en = normalize_name(db_fname_en)
    lname_en = normalize_name(db_lname_en)
    fname_th = normalize_name(db_fname_th)
    lname_th = normalize_name(db_lname_th)
    
    # 1. Check Thai Full Match
    if fname_th and lname_th and (fname_th in api_norm) and (lname_th in api_norm):
        return True
        
    # 2. Check English Match (Allowing for First Initial + Last Name)
    if lname_en and lname_en in api_norm:
        # If last name matches, check if first name matches or at least first initial matches
        if fname_en and fname_en in api_norm:
            return True
        if fname_en and len(fname_en) > 0 and fname_en[0] in api_norm:
            return True
            
    return False

def search_scholar_profiles(query):
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
        return data.get("profiles", {}).get("authors", [])
    except Exception as e:
        print(f"    -> Error searching profiles for {query}: {e}")
        return []

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
        
        cursor.execute("""
            SELECT id, fname, lname, fname_en, lname_en, scholar_id
            FROM api.faculty
            ORDER BY id ASC
        """)
        faculty_list = cursor.fetchall()
        print(f"Verifying {len(faculty_list)} faculty members...")
        
        for fid, fname_th, lname_th, fname_en, lname_en, existing_id in faculty_list:
            fullname_th = f"{fname_th} {lname_th}".strip()
            fullname_en = f"{fname_en} {lname_en}".strip()
            print(f"\n[{fid}] Verifying: {fullname_en} ({fullname_th})")
            
            queries_to_try = [
                f"{fname_en} {lname_en}",
                f"{fname_th} {lname_th}",
                # Try with university name if needed
                f"{fname_en} {lname_en} Naresuan University",
                f"{fname_th} {lname_th} Naresuan University",
            ]
            
            valid_author_id = None
            valid_api_name = None
            
            # Step 1: Search profiles and verify name
            for query in queries_to_try:
                if not query.strip() or query.strip() == "Naresuan University":
                    continue
                    
                print(f"  -> Searching profiles with: '{query}'")
                profiles = search_scholar_profiles(query)
                time.sleep(1) # Rate limit
                
                for profile in profiles:
                    api_name = profile.get("name", "")
                    api_author_id = profile.get("author_id", "")
                    affiliations = profile.get("affiliations", "")
                    
                    print(f"    -> Found profile: '{api_name}' (ID: {api_author_id}) - {affiliations}")
                    
                    # Strict Name Check
                    if check_name_match(api_name, fname_en, lname_en, fname_th, lname_th):
                        valid_author_id = api_author_id
                        valid_api_name = api_name
                        print(f"    -> [MATCH] Name matches our database!")
                        break
                    else:
                        print(f"    -> [MISMATCH] Name does not match database.")
                
                if valid_author_id:
                    break # Stop trying queries if we found a match
            
            # Step 2: Update Database
            if valid_author_id:
                print(f"  -> Fetching complete data for {valid_api_name} ({valid_author_id})...")
                author_data = fetch_author_data(valid_author_id)
                time.sleep(1)
                
                if author_data:
                    # Final check on author data name just to be absolutely sure
                    author_info = author_data.get("author", {})
                    final_name = author_info.get("name", valid_api_name)
                    
                    if check_name_match(final_name, fname_en, lname_en, fname_th, lname_th):
                        articles = author_data.get("articles", [])
                        cited_by = author_data.get("cited_by", {})
                        
                        cursor.execute("""
                            UPDATE api.faculty 
                            SET scholar_id = %s, scholar_data = %s, cited = %s
                            WHERE id = %s
                        """, (
                            valid_author_id,
                            json.dumps(articles, ensure_ascii=False),
                            json.dumps(cited_by, ensure_ascii=False),
                            fid
                        ))
                        conn.commit()
                        print(f"  -> SUCCESS! Saved {len(articles)} articles.")
                    else:
                        print(f"  -> ERROR: Final author name '{final_name}' failed strict check! Aborting update.")
                        cursor.execute("UPDATE api.faculty SET scholar_id = NULL, scholar_data = NULL, cited = NULL WHERE id = %s", (fid,))
                        conn.commit()
                else:
                    print(f"  -> FAILED to fetch full author data.")
            else:
                print(f"  -> No valid matching profile found. Clearing existing Scholar data.")
                cursor.execute("UPDATE api.faculty SET scholar_id = NULL, scholar_data = NULL, cited = NULL WHERE id = %s", (fid,))
                conn.commit()
                
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

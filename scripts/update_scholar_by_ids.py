import psycopg2
import json
import requests
import time
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    PG_HOST = os.getenv("DB_HOST", "10.10.58.21")
    PG_USER = "agi"
    PG_PASS = os.getenv("DB_PASSWORD", "")
    PG_DB   = "nred"
    SERP_API_KEY = os.getenv("SERP_API_KEY", "").strip()

    if not SERP_API_KEY:
        print("Error: Missing SERP_API_KEY in environment variables.")
        return

    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
        cursor = conn.cursor()
        print("Connected to PostgreSQL database successfully.")

        # Fetch all faculty with non-empty scholar_id
        cursor.execute("""
            SELECT id, fname, lname, fname_en, lname_en, scholar_id 
            FROM api.faculty 
            WHERE scholar_id IS NOT NULL AND scholar_id != ''
            ORDER BY id ASC
        """)
        faculty_members = cursor.fetchall()
        print(f"Found {len(faculty_members)} faculty members with valid Google Scholar IDs.")

        success_count = 0
        failed_count = 0

        for fid, fname_th, lname_th, fname_en, lname_en, scholar_id in faculty_members:
            fullname_th = f"{fname_th} {lname_th}".strip()
            fullname_en = f"{fname_en} {lname_en}".strip() if fname_en else fullname_th
            print(f"\n[{fid}] Processing: {fullname_en} (Scholar ID: {scholar_id})")

            # Call SerpApi Google Scholar Author API
            url = "https://serpapi.com/search.json"
            params = {
                "engine": "google_scholar_author",
                "hl": "en",
                "author_id": scholar_id,
                "api_key": SERP_API_KEY
            }

            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                author_data = response.json()

                if "error" in author_data:
                    print(f"  -> SerpApi returned error: {author_data['error']}")
                    failed_count += 1
                    continue

                author_info = author_data.get("author", {})
                articles = author_data.get("articles", [])
                cited_by = author_data.get("cited_by", {})

                print(f"  -> Successfully fetched data for {author_info.get('name', fullname_en)}")
                print(f"  -> Articles found: {len(articles)}")
                print(f"  -> Citation metrics: {cited_by.get('table', [])}")

                # Update database
                cursor.execute("""
                    UPDATE api.faculty 
                    SET scholar_data = %s, cited = %s, updated_at = NOW()
                    WHERE id = %s
                """, (
                    json.dumps(articles, ensure_ascii=False),
                    json.dumps(cited_by, ensure_ascii=False),
                    fid
                ))
                conn.commit()
                print(f"  -> Database updated successfully!")
                success_count += 1

            except Exception as e:
                print(f"  -> Error fetching/updating for Scholar ID {scholar_id}: {e}")
                failed_count += 1

            # Sleep to respect rate limits
            time.sleep(1)

        print(f"\n==========================================")
        print(f"Scholar Data Update Completed!")
        print(f"Successfully updated: {success_count} members.")
        print(f"Failed: {failed_count} members.")
        print(f"==========================================")

    except Exception as e:
        print(f"Database connection error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("PostgreSQL connection closed.")

if __name__ == "__main__":
    main()

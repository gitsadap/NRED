import asyncio
import aiomysql
import json
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
MYSQL_DB = os.getenv("MYSQL_DB", "db_user").strip()

async def check_names():
    try:
        if not MYSQL_HOST or not MYSQL_USER or not MYSQL_PASSWORD:
            raise RuntimeError("Missing MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD environment variables")

        conn = await aiomysql.connect(host=MYSQL_HOST, port=MYSQL_PORT,
                                      user=MYSQL_USER, password=MYSQL_PASSWORD,
                                      db=MYSQL_DB, charset='tis620',
                                      cursorclass=aiomysql.DictCursor)
        async with conn.cursor() as cur:
            # Fetch Faculty (depart_id = 4)
            sql = "SELECT user_id, fname, lname, fname_eng, lname_eng FROM user WHERE depart_id = 4"
            await cur.execute(sql)
            result = await cur.fetchall()
            
            print(f"Found {len(result)} faculty members.")
            for row in result:
                # Handle possible None values before printing
                fname = row.get('fname') or ""
                lname = row.get('lname') or ""
                fname_eng = row.get('fname_eng') or ""
                lname_eng = row.get('lname_eng') or ""

                print(f"ID: {row['user_id']}")
                print(f"  TH: {fname.strip()} {lname.strip()}")
                print(f"  EN: '{fname_eng.strip()}' '{lname_eng.strip()}'")
                print("-" * 20)

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_names())

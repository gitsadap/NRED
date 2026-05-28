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

async def inspect():
    try:
        if not MYSQL_HOST or not MYSQL_USER or not MYSQL_PASSWORD:
            raise RuntimeError("Missing MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD environment variables")

        conn = await aiomysql.connect(host=MYSQL_HOST, port=MYSQL_PORT,
                                      user=MYSQL_USER, password=MYSQL_PASSWORD,
                                      db=MYSQL_DB, charset='tis620',
                                      cursorclass=aiomysql.DictCursor)
        async with conn.cursor() as cur:
            print("--- User Table columns ---")
            await cur.execute("SHOW COLUMNS FROM user")
            print(json.dumps(await cur.fetchall(), default=str, indent=2))
            
            print("\n--- Sample Position Data ---")
            await cur.execute("SELECT * FROM academic_position LIMIT 5")
            print(json.dumps(await cur.fetchall(), default=str, ensure_ascii=False, indent=2))

            print("\n--- Sample Prefix Data ---")
            await cur.execute("SELECT * FROM prefix LIMIT 5")
            print(json.dumps(await cur.fetchall(), default=str, ensure_ascii=False, indent=2))

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())

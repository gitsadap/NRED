import asyncio
import aiomysql
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def inspect():
    host = os.getenv("MYSQL_HOST", "").strip()
    user = os.getenv("MYSQL_USER", "").strip()
    pw = os.getenv("MYSQL_PASSWORD", "").strip()
    dbname = os.getenv("MYSQL_DB", "db_user").strip()
    if not host or not user or not pw:
        raise RuntimeError("Missing MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD environment variables")

    print(f"Connecting to {host}...")
    try:
        conn = await aiomysql.connect(host=host, port=3306, user=user, password=pw, db=dbname, charset='tis620', cursorclass=aiomysql.DictCursor)
        
        async with conn.cursor() as cursor:
            # Check user table columns
            print("\n--- Columns in 'user' ---")
            await cursor.execute("SHOW COLUMNS FROM user")
            columns = await cursor.fetchall()
            for c in columns:
                print(f"{c['Field']} ({c['Type']})")
                
            # Dump a few rows to check data
            print("\n--- Sample data from 'user' ---")
            await cursor.execute("SELECT * FROM user LIMIT 3")
            rows = await cursor.fetchall()
            print(json.dumps(rows, default=str, ensure_ascii=False, indent=2))

        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())

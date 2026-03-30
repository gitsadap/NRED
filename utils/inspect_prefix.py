import asyncio
import aiomysql
import json

async def inspect():
    host = "10.10.58.16"
    user = "gitsadap"
    pw = "it[[{ko-hv,^]8ItgdK9i"
    dbname = "db_user"

    print(f"Connecting to {host}...")
    try:
        conn = await aiomysql.connect(host=host, port=3306, user=user, password=pw, db=dbname, charset='tis620', cursorclass=aiomysql.DictCursor)
        
        async with conn.cursor() as cursor:
            # Check prefix columns
            print("\n--- Columns in 'prefix' ---")
            await cursor.execute("SHOW COLUMNS FROM prefix")
            columns = await cursor.fetchall()
            for c in columns:
                print(f"{c['Field']} ({c['Type']})")
                
            # Dump full content of prefix
            print("\n--- Content of 'prefix' ---")
            await cursor.execute("SELECT * FROM prefix")
            rows = await cursor.fetchall()
            print(json.dumps(rows, default=str, ensure_ascii=False, indent=2))

        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())

import asyncio
import aiomysql
import json

async def inspect():
    try:
        conn = await aiomysql.connect(host='10.10.58.16', port=3306,
                                      user='gitsadap', password='it[[{ko-hv,^]8ItgdK9i',
                                      db='db_user', charset='tis620',
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

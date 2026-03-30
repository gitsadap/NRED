import asyncio
import aiomysql
import json

async def check_names():
    try:
        conn = await aiomysql.connect(host='10.10.58.16', port=3306,
                                      user='gitsadap', password='it[[{ko-hv,^]8ItgdK9i',
                                      db='db_user', charset='tis620',
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

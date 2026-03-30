import asyncio
import aiomysql
import json

async def reproduce():
    host = "10.10.58.16"
    user = "gitsadap"
    pw = "it[[{ko-hv,^]8ItgdK9i"
    dbname = "db_user"

    print(f"Connecting to {host}...")
    try:
        conn = await aiomysql.connect(host=host, port=3306, user=user, password=pw, db=dbname, charset='tis620', cursorclass=aiomysql.DictCursor)
        print("Connected successfully!")
        
        async with conn.cursor() as cur:
            sql = """
                SELECT 
                    u.*, 
                    p.prefix_name AS prefix, 
                    ap.th_name AS acad_pos,
                    pos.position_name AS position
                FROM `user` u
                LEFT JOIN prefix p ON u.prefix_id = p.prefix_id
                LEFT JOIN academic_position ap ON u.acad_pos_id = ap.acad_pos_id
                LEFT JOIN position pos ON u.position_id = pos.position_id
                WHERE u.depart_id = 4
                ORDER BY u.acad_pos_id ASC, u.fname ASC, u.lname ASC
            """
            print("Executing SQL...")
            await cur.execute(sql)
            result = await cur.fetchall()
            print(f"Got {len(result)} rows.")
            
            for row in result:
                 # Replicating the logic in public.py
                acad_pos_name = row.get('acad_pos', '') or ''
                raw_prefix = row.get('prefix', '') or ''
                display_prefix = raw_prefix
                
                has_dr = "ดร." in raw_prefix
                
                if has_dr:
                    display_prefix = "ดร."
                else:
                    if raw_prefix == acad_pos_name:
                        display_prefix = "" 
                    
                    academic_prefixes = ["ศาสตราจารย์", "รองศาสตราจารย์", "ผู้ช่วยศาสตราจารย์", "อาจารย์"]
                    if raw_prefix in academic_prefixes:
                        display_prefix = ""
                
                fname = row.get('fname', '')
                lname = row.get('lname', '')
                
                display_name = f"{display_prefix} {fname} {lname}".strip()
                print(f"Processed: {display_name} | {acad_pos_name}")

        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())

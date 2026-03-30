import asyncio
import asyncpg
import os

DATABASE_URL = (os.getenv("DATABASE_URL") or "")

async def seed_awards():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected to database")

        # Clear existing awards (optional, maybe keep?)
        # await conn.execute("DELETE FROM api.awards")
        # print("Cleared existing awards")

        awards_data = [
            {
                "title": "NRCT Quality Achievement Award",
                "description": "ขอแสดงความยินดีกับ รองศาสตราจารย์ ดร.นัฐพล มหาวิค และคณะ ได้รับรางวัลผลงานคุณภาพ ประเภทผลงานวิจัย สาขาวิทยาศาสตร์กายภาพและคณิตศาสตร์",
                "image_url": "https://placehold.co/1200x500/0047AB/FFFFFF?text=Award+1+Dr.Nathaphon",
                "icon": "academic-cap", # Fallback
                "color_theme": "blue",
                "link_url": "#",
                "order_index": 1
            },
            {
                "title": "NRCT Thesis Award",
                "description": "ขอแสดงความยินดีกับ ดร.เกศินี เอี่ยมสะอาด ได้รับรางวัลผลงานคุณภาพ ประเภทวิทยานิพนธ์ สาขาเกษตรศาสตร์และชีววิทยา",
                "image_url": "https://placehold.co/1200x500/DDA0DD/000000?text=Award+2+Dr.Kesinee",
                "icon": "academic-cap", # Fallback
                "color_theme": "purple",
                "link_url": "#",
                "order_index": 2
            }
        ]

        for award in awards_data:
            # Check if exists by title to avoid duplicates
            existing = await conn.fetchval(
                "SELECT id FROM api.awards WHERE title = $1", 
                award["title"]
            )
            
            if existing:
                print(f"Updating award: {award['title']}")
                await conn.execute("""
                    UPDATE api.awards 
                    SET description = $2, image_url = $3, icon = $4, color_theme = $5, link_url = $6, order_index = $7
                    WHERE id = $1
                """, existing, award["description"], award["image_url"], award["icon"], award["color_theme"], award["link_url"], award["order_index"])
            else:
                print(f"Inserting award: {award['title']}")
                await conn.execute("""
                    INSERT INTO api.awards (title, description, image_url, icon, color_theme, link_url, order_index)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, award["title"], award["description"], award["image_url"], award["icon"], award["color_theme"], award["link_url"], award["order_index"])

        print("Awards seeded successfully")
        await conn.close()
    
    except Exception as e:
        print(f"Error seeding awards: {e}")

if __name__ == "__main__":
    asyncio.run(seed_awards())

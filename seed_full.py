import asyncio
from datetime import datetime
import json
from app.database import engine
from app.models import Base, Page, News, Activity, Staff, Menu, Setting, User
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def seed_full():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("Seeding full database...")

        # 1. Admin User
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
             # In real app use hash. For now just placeholder string as logic handles comparison
             # But wait, original PHP used password_hash. Python passlib?
             # For simplicity and "simulation", I'll just insert a dummy hash that matches "password123" if I had checking logic.
             # Note: My Auth logic in Python isn't fully implemented with hashing yet, but I'll add the user.
             # Actually I should implement Auth properly. But for now, let's just seed.
             admin = User(username="admin", password_hash="dummy_hash_for_password123")
             session.add(admin)
             print(" - Admin user created")

        # 2. Settings
        settings = {
            'site_title': 'Department of Agricultural Science',
            'footer_text': '© 2024 Department of Agricultural Science. All Rights Reserved.',
            'hero_mode': 'slider',
            'hero_slider_images': '["https://images.unsplash.com/photo-1500382017468-9049fed747ef?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80"]',
            'hero_title': 'ภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม',
            'hero_subtitle': 'สร้างสรรค์นวัตกรรม เพื่อความยั่งยืนของโลก',
            'hero_btn_text': 'รู้จักเราให้มากขึ้น',
            'hero_btn_url': '/about',
            'quick_buttons_json': json.dumps([
                 {'title': 'วิทยาศาสตร์สิ่งแวดล้อม', 'url': '/curriculum/env-science', 'color': 'green', 'image': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'},
                 {'title': 'เทคโนโลยีและการจัดการ', 'url': '/curriculum/tech-management', 'color': 'teal', 'image': 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'},
                 {'title': 'ภูมิศาสตร์', 'url': '/curriculum/geography', 'color': 'blue', 'image': 'https://images.unsplash.com/photo-1524661135-423995f22d0b?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'},
                 {'title': 'ภูมิสารสนเทศ', 'url': '/curriculum/gis', 'color': 'indigo', 'image': 'https://images.unsplash.com/photo-1569336415962-a4bd9f69cd83?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'},
                 {'title': 'ระบบประชุมภาควิชา', 'url': 'https://oassar.agi.nu.ac.th/nredmeet/', 'color': 'green', 'image': ''},
                 {'title': 'ระบบยืมคืนเครื่องแก้ว ห้องปฏิบัติการทรัพยากรธรรมชาติและวิทยาศาสตร์สิ่งแวดล้อม', 'url': 'https://oassar.agi.nu.ac.th/nrelab/', 'color': 'orange', 'image': ''},
                 {'title': 'รายการเครื่องมือวิทยาศาสตร์', 'url': 'https://ww2.agi.nu.ac.th/sciencelab/department.php?ag=4', 'color': 'teal', 'image': ''},
                 {'title': 'ขอใช้เครื่องมือวิทยาศาสตร์', 'url': 'http://conf.agi.nu.ac.th/agro/Main/Logon.aspx', 'color': 'red', 'image': ''},
                 {'title': 'จองห้องเรียน ห้องประชุม', 'url': 'https://ww2.agi.nu.ac.th/booking_room/', 'color': 'indigo', 'image': ''},
            ]),
            'home_features_json': json.dumps([
                {'title': 'วิทยาศาสตร์เกษตร', 'desc': 'ผู้นำการวิจัยเพื่อการผลิตพืช ปฐพีศาสตร์ และระบบเกษตรยั่งยืนเพื่ออนาคต.', 'icon': 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z', 'url': '/research/agriculture', 'color': 'text-green-600'},
                {'title': 'สัตวศาสตร์', 'desc': 'พัฒนาสุขภาวะสัตว์ โภชนาการ และพันธุศาสตร์ เพื่อความมั่นคงทางอาหารโลก.', 'icon': 'M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z', 'url': '/research/animal-science', 'color': 'text-yellow-600'},
                {'title': 'ประมง', 'desc': 'การจัดการทรัพยากรทางน้ำอย่างยั่งยืนและนวัตกรรมเทคโนโลยีการเพาะเลี้ยงสัตว์น้ำ.', 'icon': 'M13 10V3L4 14h7v7l9-11h-7z', 'url': '/research/fisheries', 'color': 'text-green-600'}
            ]),
            'stats_json': json.dumps([
                {'number': '22', 'label': 'หลักสูตร', 'icon': 'graduation-cap'},
                {'number': '1424', 'label': 'นิสิตปัจจุบัน', 'icon': 'id-card'},
                {'number': '4892', 'label': 'สำเร็จการศึกษา', 'icon': 'users'},
                {'number': '134', 'label': 'บุคลากร', 'icon': 'user-circle'},
                {'number': '3', 'label': 'ภาควิชา', 'icon': 'building'},
            ])
        }
        for k, v in settings.items():
            await session.merge(Setting(key=k, value=v))
        print(" - Settings seeded")

        # 3. Menus (Main Menu)
        menu_items = [
            {"label": "หน้าแรก", "url": "/"},
            {"label": "เกี่ยวกับเรา", "url": "/about", "children": [
                {"label": "ประวัติความเป็นมา", "url": "/history"},
                {"label": "วิสัยทัศน์ / พันธกิจ", "url": "/vision"},
                {"label": "โครงสร้างองค์กร", "url": "/structure"},
                {"label": "บุคลากร", "url": "/faculty"},
                {"label": "ผู้บริหาร", "url": "/executives"},
                {"label": "สายสนับสนุน", "url": "/support-staff"},
            ]},
            {"label": "หลักสูตร", "url": "/curriculum", "children": [
                {"label": "ปริญญาตรี", "url": "/curriculum/bachelor"},
                {"label": "ปริญญาโท", "url": "/curriculum/master"},
                {"label": "ปริญญาเอก", "url": "/curriculum/phd"},
            ]},
            {"label": "การเข้าศึกษา", "url": "/admission"},
            {"label": "วิจัย/บริการวิชาการ", "url": "/research"},
            {"label": "ข่าวสาร", "url": "/news"},
            {"label": "กิจกรรม", "url": "/activities"},
            {"label": "ร้องเรียน/อุทธรณ์", "url": "/appeals"},
            {"label": "ติดต่อเรา", "url": "/contact"},
        ]
        await session.merge(Menu(name="main", data_json=json.dumps(menu_items)))
        print(" - Main menu seeded")

        # 4. Pages
        pages = [
            {"slug": "history", "title": "ประวัติความเป็นมา", "content": "<h1>ประวัติความเป็นมา</h1><p>ก่อตั้งเมื่อปี...</p>"},
            {"slug": "vision", "title": "วิสัยทัศน์ / พันธกิจ", "content": "<h1>วิสัยทัศน์</h1><p>เป็นผู้นำด้าน...</p>"},
            {"slug": "structure", "title": "โครงสร้างองค์กร", "content": "<p>แผนผังองค์กร...</p>"},
            {"slug": "curriculum-bachelor", "title": "หลักสูตรปริญญาตรี", "content": "<p>รายละเอียดหลักสูตร...</p>"},
            {"slug": "admission", "title": "การเข้าศึกษา", "content": "<p>ข้อมูลการรับสมัคร...</p>"},
            {"slug": "contact", "title": "ติดต่อเรา", "content": "<p>ที่อยู่...</p>"},
        ]
        for p in pages:
            existing = await session.execute(select(Page).where(Page.slug == p['slug']))
            if not existing.scalars().first():
                session.add(Page(slug=p['slug'], title=p['title'], content=p['content'], is_published=1))
        print(" - Pages seeded")

        # 5. News
        if not (await session.execute(select(News))).scalars().first():
            session.add(News(title="เปิดรับสมัครนิสิตใหม่", content="<p>รายละเอียดการรับสมัคร...</p>", category="general", created_at=datetime.now()))
            session.add(News(title="ขอเชิญร่วมงานวันเกษตร", content="<p>งานวันเกษตรแฟร์...</p>", category="general", created_at=datetime.now()))
            print(" - News seeded")

        # 6. Activities
        if not (await session.execute(select(Activity))).scalars().first():
             session.add(Activity(title="โครงการปลูกป่า", content="<p>นิสิตร่วมใจปลูกป่า...</p>", created_at=datetime.now()))
             print(" - Activities seeded")
        
        # 7. Staff
        staff_data = [
            # Executives
            {"name": "รศ.ดร.สมชาย ใจดี", "position": "หัวหน้าภาควิชา", "email": "somchai@univ.ac.th", "type": "executive", "order_index": 1},
            {"name": "ดร.วิชัย รักเรียน", "position": "รองหัวหน้าภาควิชา", "email": "wichai@univ.ac.th", "type": "executive", "order_index": 2},
            # Faculty
            {"name": "ผศ.ดร.มานี มีตา", "position": "อาจารย์ประจำ", "email": "manee@univ.ac.th", "type": "faculty", "order_index": 1, "expertise": "วิทยาศาสตร์สิ่งแวดล้อม"},
            {"name": "อ.ปิติ พอใจ", "position": "อาจารย์ประจำ", "email": "piti@univ.ac.th", "type": "faculty", "order_index": 2, "expertise": "วนศาสตร์"},
            # Support
            {"name": "นางสาวสวย ใจงาม", "position": "เจ้าหน้าที่ธุรการ", "email": "suay@univ.ac.th", "type": "support", "order_index": 1},
        ]
        
        for s in staff_data:
            session.add(Staff(**s))
        print(" - Staff seeded")

        await session.commit()
        print("Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_full())

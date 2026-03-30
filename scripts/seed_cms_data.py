import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Banner, Mission, Course, Statistic, Award, ContactInfo
from sqlalchemy import select

async def seed_data():
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as session:
        print("Seeding CMS Data...")

        # 1. Banners (Hero)
        banners = [
            Banner(
                title="NATURAL RESOURCES ENVIRONMENT DEPARTMENT",
                subtitle="ภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม คณะเกษตรศาสตร์ ทรัพยากรธรรมชาติและสิ่งแวดล้อม มหาวิทยาลัยนเรศวร",
                video_url="/assets/images/NRED-bg.mp4",
                order_index=1
            )
        ]
        
        # 2. Missions (Flip Carousel)
        missions = [
            Mission(title="Academic Excellence", desc="มุ่งสู่ความเป็นเลิศทางวิชาการและการวิจัย", icon="academic-cap", color="green", order_index=1),
            Mission(title="Innovation", desc="สร้างสรรค์นวัตกรรมเพื่อการจัดการทรัพยากร", icon="beaker", color="blue", order_index=2),
            Mission(title="Sustainability", desc="ส่งเสริมความยั่งยืนของสิ่งแวดล้อม", icon="globe", color="cyan", order_index=3),
            Mission(title="Community", desc="บริการวิชาการแก่สังคมและชุมชน", icon="users", color="indigo", order_index=4),
            Mission(title="Global Network", desc="สร้างเครือข่ายความร่วมมือระดับนานาชาติ", icon="globe", color="purple", order_index=5),
            Mission(title="Research", desc="พัฒนางานวิจัยเพื่อแก้ปัญหาประเทศ", icon="cog", color="teal", order_index=6)
        ]

        # 3. Courses (Video Grid)
        courses = [
            Course(
                title_th="ทรัพยากรธรรมชาติและสิ่งแวดล้อม",
                title_en="Natural Resources and Environment",
                video_url="caim_9VAOkk",
                color_theme="green",
                order_index=1
            ),
            Course(
                title_th="ภูมิศาสตร์",
                title_en="Geography",
                video_url="WRqiXQ-8Sa0",
                color_theme="indigo",
                order_index=2
            ),
            Course(
                title_th="วิทยาศาสตร์สิ่งแวดล้อม",
                title_en="Environmental Science",
                video_url="L_K3Og0CV8I",
                color_theme="teal",
                order_index=3
            )
        ]

        # 4. Hall of Fame (Awards)
        awards = [
            Award(
                title="นิสิตดีเด่น",
                description="ขอแสดงความยินดีกับนิสิตสาขาวิชาภูมิศาสตร์ ที่ได้รับรางวัลจากการนำเสนอผลงานวิจัยระดับชาติ",
                icon="academic-cap",
                color_theme="yellow",
                order_index=1
            ),
            Award(
                title="ผลงานวิชาการ",
                description="อาจารย์ภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม ได้รับการตีพิมพ์ผลงานวิจัยในวารสารระดับนานาชาติ Q1",
                icon="beaker",
                color_theme="blue",
                order_index=2
            ),
            Award(
                title="รางวัลนวัตกรรม",
                description="ทีมวิจัยสิ่งแวดล้อมคว้ารางวัลชนะเลิศ การประกวดยูทูปเบอร์รักษ์โลก ปี 2568",
                icon="globe",
                color_theme="purple",
                order_index=3
            )
        ]

        # 5. Statistics
        stats = [
            Statistic(label="Students", value=500, suffix="+", icon="users", order_index=1),
            Statistic(label="Graduates", value=2000, suffix="+", icon="academic-cap", order_index=2),
            Statistic(label="Research", value=150, suffix="+", icon="beaker", order_index=3),
            Statistic(label="Awards", value=50, suffix="+", icon="award", order_index=4)
        ]

        # 6. Contact Info
        contacts = [
            ContactInfo(key="address", value="99 หมู่ 9 ต.ท่าโพธิ์ อ.เมือง จ.พิษณุโลก 65000"),
            ContactInfo(key="phone", value="0-5596-2710"),
            ContactInfo(key="email", value="aggie@nu.ac.th"),
            ContactInfo(key="facebook", value="https://www.facebook.com/NRED.NU")
        ]

        # Helper to seed if empty
        async def seed_if_empty(model, data_list):
            result = await session.execute(select(model))
            if not result.scalars().first():
                session.add_all(data_list)
                print(f"Seeded {len(data_list)} items for {model.__name__}")
            else:
                print(f"Skipping {model.__name__}, data exists.")

        await seed_if_empty(Banner, banners)
        await seed_if_empty(Mission, missions)
        await seed_if_empty(Course, courses)
        await seed_if_empty(Award, awards)
        await seed_if_empty(Statistic, stats)
        await seed_if_empty(ContactInfo, contacts)

        await session.commit()
        print("Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())

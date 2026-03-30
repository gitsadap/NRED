import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# ตรวจสอบว่า DATABASE_URL เป็น postgresql+asyncpg://...
DATABASE_URL = settings.database_url

# สร้าง Engine พร้อมปิด Statement Cache อย่างถาวรสำหรับ Supabase/PgBouncer
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_size=3,           # ปรับลดลงเหลือ 3 เพื่อความเสถียรบน Vercel Free
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        # บรรทัดเหล่านี้สำคัญมาก ห้ามขาดตัวใดตัวหนึ่งครับ
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0, 
        "command_timeout": 60,
        "server_settings": {
            "application_name": "nred_agi_prod"
        }
    }
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
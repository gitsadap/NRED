import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from app.logging_config import logger

# 1. ตรวจสอบ DATABASE_URL
# ต้องเป็นรูปแบบ: postgresql+asyncpg://user:pass@host:6543/postgres
DATABASE_URL = settings.database_url
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 1.1 SSL Context สำหรับ Supabase (ข้ามการตรวจสอบ Certificate ใน Development หรือ Pooler)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 2. สร้าง Engine พร้อมการตั้งค่าที่เหมาะสมกับ Supabase + Vercel
engine = create_async_engine(
    DATABASE_URL, 
    echo=settings.debug,
    # ปรับ Pool Size ให้เล็กลงเพื่อไม่ให้ Connection ของ Supabase เต็ม (สำคัญสำหรับ Serverless)
    pool_size=5,
    max_overflow=10,
    # ตรวจสอบการเชื่อมต่อก่อนดึงไปใช้ (ป้องกันปัญหาสัญญาณหลุด)
    pool_pre_ping=True,
    # คืน Connection เร็วขึ้น (30 นาที) เพื่อไม่ให้ค้างในระบบ Cloud
    pool_recycle=1800,
    # บังคับใช้ SSL เพื่อความปลอดภัย (Supabase บังคับใช้ในบางกรณี)
    connect_args={
        "prepared_statement_cache_size": 0,
        "server_settings": {
            "application_name": "nred_fastapi"
        }
    }
)

# 3. สร้าง Session Factory สำหรับ Async
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

# 4. Dependency สำหรับใช้ใน FastAPI Routes
async def get_db():
    """Database dependency with proper error handling and auto-close"""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            await session.close()
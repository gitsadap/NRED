utf-8import os
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from fastapi import HTTPException
from app.config import settings


DATABASE_URL = settings.database_url


engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_size=3,           
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        
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
_LAST_DB_HEALTHCHECK_AT = 0.0
_DB_HEALTHCHECK_INTERVAL_SECONDS = 15

async def get_db():
    global _LAST_DB_HEALTHCHECK_AT
    async with SessionLocal() as session:
        try:
            
            now = time.monotonic()
            if now - _LAST_DB_HEALTHCHECK_AT >= _DB_HEALTHCHECK_INTERVAL_SECONDS:
                await session.execute(text("SELECT 1"))
                _LAST_DB_HEALTHCHECK_AT = now
            yield session
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        finally:
            await session.close()
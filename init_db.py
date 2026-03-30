import asyncio
from app.database import engine, Base
from app.models import User, Page, Menu, Setting, Appeal

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Optional: Drop all to start fresh during dev
        await conn.run_sync(Base.metadata.create_all)
    print("Database Initialized")

if __name__ == "__main__":
    asyncio.run(init_models())

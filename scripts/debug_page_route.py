
import asyncio
import sys
import os

# Set path to root
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Page
from app.dependencies import get_global_context

# Use correct PG URL
DATABASE_URL = (os.getenv("DATABASE_URL") or "")

async def debug_route():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Checking get_global_context...")
        try:
            context = await get_global_context(db)
            print("Global context keys:", context.keys())
        except Exception as e:
            print(f"Error in get_global_context: {e}")
            import traceback
            traceback.print_exc()
            return

        slug = "history"
        print(f"Fetching page slug='{slug}'...")
        try:
             result = await db.execute(select(Page).where(Page.slug == slug))
             page = result.scalars().first()
             if page:
                 print(f"Page found: {page.title}")
                 # Check access to attributes
                 print(f"Template: {page.template}")
                 print(f"Content length: {len(page.content) if page.content else 0}")
             else:
                 print("Page NOT found")
        except Exception as e:
            print(f"Error fetching page: {e}")
            import traceback
            traceback.print_exc()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug_route())

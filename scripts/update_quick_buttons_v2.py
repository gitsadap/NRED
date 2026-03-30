
import asyncio
import json
from sqlalchemy import select, update
from app.database import SessionLocal
from app.models import Setting

async def main():
    async with SessionLocal() as session:
        # Fetch current settings
        result = await session.execute(select(Setting).where(Setting.key == 'quick_buttons_json'))
        setting = result.scalars().first()
        
        if not setting:
            print("Setting 'quick_buttons_json' not found.")
            return

        current_buttons = json.loads(setting.value)
        print(f"Current buttons count: {len(current_buttons)}")

        # Filter out curriculum links
        # We want to remove NRE, Geo, Env Sci, Geoinformatics
        # We will keep the systems/tools
        
        titles_to_remove = [
            "Natural Resources & Environment",
            "Environmental Science",
            "Geography",
            "Geoinformatics"
        ]
        
        new_buttons = [
            btn for btn in current_buttons 
            if btn['title'] not in titles_to_remove
        ]
        
        print(f"New buttons count: {len(new_buttons)}")
        
        # Update database
        setting.value = json.dumps(new_buttons, ensure_ascii=False)
        await session.commit()
        print("Quick buttons updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
from app.database import SessionLocal
from app.models import Setting
from sqlalchemy import select

async def main():
    async with SessionLocal() as session:
        # Define the new Quick Buttons configuration
        new_buttons = [
             {'title': 'Natural Resources & Environment', 'url': '/curriculum#nre', 'color': 'blue', 'image': ''},
             {'title': 'Environmental Science', 'url': '/curriculum#envi', 'color': 'teal', 'image': ''},
             {'title': 'Geography', 'url': '/curriculum#geo', 'color': 'indigo', 'image': ''},
             {'title': 'Geoinformatics', 'url': '/curriculum#geo', 'color': 'blue', 'image': ''},
             {'title': 'ระบบประชุมภาควิชา', 'url': 'https://oassar.agi.nu.ac.th/nredmeet/', 'color': 'green', 'image': ''},
             {'title': 'ระบบยืมคืนเครื่องแก้ว ห้องปฏิบัติการทรัพยากรธรรมชาติและวิทยาศาสตร์สิ่งแวดล้อม', 'url': 'https://oassar.agi.nu.ac.th/nrelab/', 'color': 'orange', 'image': ''},
             {'title': 'รายการเครื่องมือวิทยาศาสตร์', 'url': 'https://ww2.agi.nu.ac.th/sciencelab/department.php?ag=4', 'color': 'teal', 'image': ''},
             {'title': 'ขอใช้เครื่องมือวิทยาศาสตร์', 'url': 'http://conf.agi.nu.ac.th/agro/Main/Logon.aspx', 'color': 'red', 'image': ''},
             {'title': 'จองห้องเรียน ห้องประชุม', 'url': 'https://ww2.agi.nu.ac.th/booking_room/', 'color': 'indigo', 'image': ''},
        ]
        
        json_str = json.dumps(new_buttons, ensure_ascii=False)
        
        # Fetch existing setting
        result = await session.execute(select(Setting).where(Setting.key == 'quick_buttons_json'))
        setting = result.scalars().first()
        
        if setting:
            print("Updating existing quick_buttons_json...")
            setting.value = json_str
        else:
            print("Creating new quick_buttons_json setting...")
            new_setting = Setting(key='quick_buttons_json', value=json_str)
            session.add(new_setting)
            
        await session.commit()
        print("Database updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())

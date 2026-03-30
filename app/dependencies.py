from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Setting, Menu, ContactInfo
from app.logging_config import logger
import json

async def get_global_context(db: AsyncSession):
    """Get global context with proper error handling"""
    try:
        # Fetch Settings
        result = await db.execute(select(Setting))
        settings = {row.Setting.key: row.Setting.value for row in result}
        
        site_title = settings.get('site_title', 'Department of NRE')
        site_logo = settings.get('site_logo', '/assets/images/logo_new.png')
        site_footer = settings.get('footer_text', '© 2024 Department of NRE. All Rights Reserved.')

        # Fetch All Menus
        menu_result = await db.execute(select(Menu))
        all_menus = menu_result.scalars().all()
        
        menus = {}
        for m in all_menus:
            try:
                menus[m.name] = json.loads(m.data_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in menu {m.name}: {e}")
                menus[m.name] = []

        menu_items = menus.get('main', [])
        if not menu_items:
            # Default Fallback
            menu_items = [
                {'label': 'เกี่ยวากับเรา', 'url': '/about'},
                {'label': 'หลักสูตร', 'url': '/curriculum'},
                {'label': 'ผู้ต้องการเข้าศึกษาต่อ', 'url': '/admission'},
                {'label': 'นิสิตปัจจุบัน', 'url': '/current-students'},
                {'label': 'สหกิจศึกษา', 'url': '/coop'},
                {'label': 'ข่าวสาร', 'url': '/news'},
                {'label': 'บริการออนไลน์', 'url': '/services'},
                {'label': 'อุทธรณ์ร้องทุกข์', 'url': '/appeals'}, 
            ]
        
        # Parse JSON Settings for Home Page
        try:
            hero_slider_images = json.loads(settings.get('hero_slider_images') or '[]')
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in hero_slider_images")
            hero_slider_images = []
            
        if not hero_slider_images: 
            hero_slider_images = ['https://images.unsplash.com/photo-1500382017468-9049fed747ef?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80']
            
        try:
            quick_buttons = json.loads(settings.get('quick_buttons_json') or '[]')
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in quick_buttons_json")
            quick_buttons = []
            
        if not quick_buttons:
            quick_buttons = [
                 {'title': 'Natural Resources & Environment', 'url': '/curriculum#nre', 'color': 'blue', 'image': ''},
                 {'title': 'Environmental Science', 'url': '/curriculum#envi', 'color': 'teal', 'image': ''},
                 {'title': 'Geography', 'url': '/curriculum#geo', 'color': 'indigo', 'image': ''},
            ]

        try:
            news_categories = json.loads(settings.get('news_categories') or '["General", "Activity", "Research", "Announcement"]')
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in news_categories")
            news_categories = ["General", "Activity", "Research", "Announcement"]

        # Fetch Contacts
        try:
            contact_res = await db.execute(select(ContactInfo).order_by(ContactInfo.order_index))
            all_contacts = contact_res.scalars().all()
            contacts = [{"key": c.key, "value": c.value, "icon": c.icon} for c in all_contacts]
        except Exception as e:
            logger.error(f"Error fetching contacts: {e}")
            contacts = []

        return {
            "site_title": site_title,
            "site_logo": site_logo,
            "site_footer": site_footer,
            "menu_items": menu_items,
            "hero_slider_images": hero_slider_images,
            "quick_buttons": quick_buttons,
            "news_categories": news_categories,
            "contacts": contacts,
            "settings": settings,
        }
        
    except Exception as e:
        logger.error(f"Error in get_global_context: {e}")
        # Return minimal context to prevent complete failure
        return {
            "site_title": "Department of NRE",
            "site_logo": "/assets/images/logo_new.png",
            "site_footer": "© 2024 Department of NRE. All Rights Reserved.",
            "menu_items": [],
            "hero_slider_images": [],
            "quick_buttons": [],
            "news_categories": ["General"],
            "contacts": [],
            "settings": {},
        }

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Page, News, Activity, Appeal, Menu, Tag
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Pydantic Schemas for Admin Actions
class PageCreate(BaseModel):
    id: Optional[int] = None
    slug: str
    title: str
    content: Optional[str] = ""

class NewsCreate(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    image: Optional[str] = None
    category: Optional[str] = "General"
    tags: Optional[str] = None
    event_date: Optional[str] = None # ISO Format or YYYY-MM-DD


class ActivityCreate(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    image: Optional[str] = None
    category: Optional[str] = "Activity"
    tags: Optional[str] = None

class TagCreate(BaseModel):
    name: str

class StaffCreate(BaseModel):
    id: Optional[int] = None
    name: str
    position: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None
    expertise: Optional[str] = None
    type: str = "faculty"


class DeleteRequest(BaseModel):
    id: int # or filename for media

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

class MenuCreate(BaseModel):
    name: str
    data_json: str # We receive stringified JSON

class BannerCreate(BaseModel):
    id: Optional[int] = None
    title: str
    subtitle: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[int] = 1
    order_index: Optional[int] = 0

class MissionCreate(BaseModel):
    id: Optional[int] = None
    title: str
    desc: Optional[str] = None
    icon: str
    color: Optional[str] = "green"
    order_index: Optional[int] = 0

class CourseCreate(BaseModel):
    id: Optional[int] = None
    title_th: str
    title_en: Optional[str] = None
    video_url: str
    description: Optional[str] = None
    color_theme: Optional[str] = "green"
    order_index: Optional[int] = 0

class StatCreate(BaseModel):
    id: Optional[int] = None
    label: str
    value: int
    suffix: Optional[str] = None
    icon: Optional[str] = None
    order_index: Optional[int] = 0

class AwardCreate(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    color_theme: Optional[str] = "yellow"
    link_url: Optional[str] = None
    order_index: Optional[int] = 0

class FacultyCreate(BaseModel):
    id: Optional[int] = None
    prefix: Optional[str] = None
    fname: str
    lname: str
    fname_en: Optional[str] = None
    lname_en: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    image: Optional[str] = None
    major: Optional[str] = None
    admin_position: Optional[str] = None
    is_expert: Optional[bool] = False
    expertise: Optional[str] = None # Expect JSON string or raw text

class ContactInfoCreate(BaseModel):
    key: str
    value: str
    icon: Optional[str] = None
    order_index: Optional[int] = 0

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context={"request": request})

# API Endpoints used by Dashboard

@router.get("/api/pages")
async def get_admin_pages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).order_by(desc(Page.updated_at)))
    return result.scalars().all()

@router.get("/api/news")
async def get_admin_news(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(News).order_by(desc(News.created_at)))
    return result.scalars().all()

@router.get("/api/activities")
async def get_admin_activities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).order_by(desc(Activity.created_at)))
    return result.scalars().all()

@router.get("/api/appeals")
async def get_admin_appeals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appeal).order_by(desc(Appeal.created_at)))
    return result.scalars().all()

@router.post("/api/appeals/delete")
async def delete_appeal(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appeal).where(Appeal.id == req.id))
    db_appeal = result.scalars().first()
    if db_appeal:
        await db.delete(db_appeal)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}

# TODO: Add POST/PUT/DELETE endpoints for full functionality

# Models moved to top

# --- Pages API ---

@router.post("/api/pages")
async def save_page(page: PageCreate, db: AsyncSession = Depends(get_db)):
    if page.id:
        result = await db.execute(select(Page).where(Page.id == page.id))
        db_page = result.scalars().first()
        if db_page:
            db_page.title = page.title
            db_page.slug = page.slug
            db_page.content = page.content
            # db_page.updated_at = func.now() # Auto updated
    else:
        # Check slug
        result = await db.execute(select(Page).where(Page.slug == page.slug))
        if result.scalars().first():
             return {"success": False, "message": "Slug already exists"}
        
        new_page = Page(slug=page.slug, title=page.title, content=page.content, is_published=1)
        db.add(new_page)
    
    await db.commit()
    return {"success": True}

@router.post("/api/pages/delete")
async def delete_page(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.id == req.id))
    db_page = result.scalars().first()
    if db_page:
        await db.delete(db_page)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}

# --- News API ---

@router.post("/api/news")
async def save_news(news: NewsCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    
    # helper for date parsing
    evt_date = None
    if news.event_date:
        try:
            evt_date = datetime.fromisoformat(news.event_date.replace('Z', '+00:00'))
        except:
            pass

    if news.id:
        result = await db.execute(select(News).where(News.id == news.id))
        db_news = result.scalars().first()
        if db_news:
            db_news.title = news.title
            db_news.content = news.content
            db_news.image_url = news.image
            db_news.category = news.category
            db_news.tags = news.tags
            db_news.event_date = evt_date
    else:
        new_news = News(
            title=news.title, 
            content=news.content, 
            image_url=news.image, 
            category=news.category or "General",
            tags=news.tags,
            event_date=evt_date,
            created_at=datetime.now()
        )
        db.add(new_news)
    
    await db.commit()
    return {"success": True}

@router.post("/api/news/delete")
async def delete_news(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(News).where(News.id == req.id))
    db_news = result.scalars().first()
    if db_news:
        await db.delete(db_news)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}

# --- Activities API ---

@router.post("/api/activities")
async def save_activity(act: ActivityCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    if act.id:
        result = await db.execute(select(Activity).where(Activity.id == act.id))
        db_act = result.scalars().first()
        if db_act:
            db_act.title = act.title
            db_act.content = act.content
            db_act.image_url = act.image
            db_act.category = act.category or "Activity"
            db_act.tags = act.tags
    else:
        new_act = Activity(
            title=act.title, 
            content=act.content, 
            image_url=act.image,
            category=act.category or "Activity",
            tags=act.tags,
            created_at=datetime.now()
        )
        db.add(new_act)
    
    await db.commit()
    return {"success": True}

@router.post("/api/activities/delete")
async def delete_activity(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == req.id))
    db_act = result.scalars().first()
    if db_act:
        await db.delete(db_act)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}

# --- Unified Content Endpoints ---
from app.models import Tag

class ContentCreate(BaseModel):
    id: Optional[int] = None
    type: str = "news" # news or activity
    title: str
    content: str
    image: Optional[str] = None
    category: Optional[str] = "General"
    tags: Optional[str] = None
    event_date: Optional[str] = None

@router.get("/api/content/all")
async def get_all_content(db: AsyncSession = Depends(get_db)):
    # Fetch News
    n_res = await db.execute(select(News).order_by(desc(News.created_at)))
    news = n_res.scalars().all()
    
    # Fetch Activities
    a_res = await db.execute(select(Activity).order_by(desc(Activity.created_at)))
    acts = a_res.scalars().all()
    
    combined = []
    for n in news:
        combined.append({
            "id": n.id,
            "type": "news",
            "title": n.title,
            "category": n.category,
            "tags": n.tags,
            "created_at": n.created_at,
            "event_date": n.event_date,
            "image_url": n.image_url,
            "content": n.content
        })
    for a in acts:
        combined.append({
            "id": a.id,
            "type": "activity",
            "title": a.title,
            "category": a.category,
            "tags": a.tags,
            "created_at": a.created_at,
            "event_date": a.event_date,
            "image_url": a.image_url,
            "content": a.content
        })
        
    # Sort by created_at desc
    combined.sort(key=lambda x: x['created_at'] or x['id'], reverse=True)
    return combined

@router.post("/api/content/save")
async def save_unified_content(item: ContentCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    
    evt_date = None
    if item.event_date:
        try:
            evt_date = datetime.fromisoformat(item.event_date.replace('Z', '+00:00'))
        except:
            pass

    if item.type == 'news':
        if item.id:
            res = await db.execute(select(News).where(News.id == item.id))
            db_obj = res.scalars().first()
            if db_obj:
                db_obj.title = item.title
                db_obj.content = item.content
                db_obj.image_url = item.image
                db_obj.category = item.category
                db_obj.tags = item.tags
                db_obj.event_date = evt_date
        else:
            db_obj = News(
                title=item.title,
                content=item.content,
                image_url=item.image,
                category=item.category or "General",
                tags=item.tags,
                event_date=evt_date,
                created_at=datetime.now()
            )
            db.add(db_obj)
            
    elif item.type == 'activity':
        if item.id:
            res = await db.execute(select(Activity).where(Activity.id == item.id))
            db_obj = res.scalars().first()
            if db_obj:
                db_obj.title = item.title
                db_obj.content = item.content
                db_obj.image_url = item.image
                db_obj.category = item.category
                db_obj.tags = item.tags
                db_obj.event_date = evt_date
        else:
            db_obj = Activity(
                title=item.title,
                content=item.content,
                image_url=item.image,
                category=item.category or "Activity",
                tags=item.tags,
                event_date=evt_date,
                created_at=datetime.now()
            )
            db.add(db_obj)

    await db.commit()
    return {"success": True}

class ContentDelete(BaseModel):
    id: int
    type: str

@router.post("/api/content/delete")
async def delete_unified_content(item: ContentDelete, db: AsyncSession = Depends(get_db)):
    if item.type == 'news':
        await db.execute(delete(News).where(News.id == item.id))
    elif item.type == 'activity':
        await db.execute(delete(Activity).where(Activity.id == item.id))
    
    await db.commit()
    return {"success": True}

# --- Tag Endpoints ---
class TagCreate(BaseModel):
    name: str

@router.get("/api/tags")
async def get_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()

@router.post("/api/tags")
async def save_tag(tag: TagCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).where(Tag.name == tag.name))
    if result.scalars().first():
        return {"success": False, "message": "Tag already exists"}
    
    new_tag = Tag(name=tag.name)
    db.add(new_tag)
    await db.commit()
    return {"success": True}

class TagDelete(BaseModel):
    id: int

@router.post("/api/tags/delete")
async def delete_tag(tag: TagDelete, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Tag).where(Tag.id == tag.id))
    await db.commit()
    return {"success": True}

# --- Staff API ---

from app.models import Staff

@router.get("/api/staff")
async def get_admin_staff(type: str = "faculty", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Staff).where(Staff.type == type).order_by(Staff.order_index))
    return result.scalars().all()

@router.post("/api/staff")
async def save_staff(staff: StaffCreate, db: AsyncSession = Depends(get_db)):
    if staff.id:
        result = await db.execute(select(Staff).where(Staff.id == staff.id))
        db_staff = result.scalars().first()
        if db_staff:
            db_staff.name = staff.name
            db_staff.position = staff.position
            db_staff.email = staff.email
            db_staff.image = staff.image
            db_staff.expertise = staff.expertise
            db_staff.type = staff.type
    else:
        new_staff = Staff(
            name=staff.name,
            position=staff.position,
            email=staff.email,
            image=staff.image,
            expertise=staff.expertise,
            type=staff.type
        )
        db.add(new_staff)
    
    await db.commit()
    return {"success": True}

@router.post("/api/staff/delete")
async def delete_staff(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Staff).where(Staff.id == req.id))
    db_staff = result.scalars().first()
    if db_staff:
        await db.delete(db_staff)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}

# --- Media API ---

from fastapi import UploadFile, File
import shutil
import os
from app.tasks import process_document_to_blob

UPLOAD_DIR = "public/uploads"
if not os.environ.get("VERCEL"):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
else:
    # ถ้าอยู่บน Vercel ให้ใช้โฟลเดอร์ /tmp แทน (เป็นที่เดียวที่ Vercel ยอมให้เขียนไฟล์ชั่วคราวได้)
    UPLOAD_DIR = "/tmp"
@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"{UPLOAD_DIR}/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # Background optimize access and path-to-blob transformation using Celery
        try:
            process_document_to_blob.delay(file_location)
        except Exception as celery_err:
            pass # ignore broker errors gracefully if redis is down
            
        return {"location": f"/uploads/{file.filename}"} # TinyMCE expects 'location'
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/media")
async def get_media_files():
    files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if not filename.startswith('.'):
                files.append({"name": filename, "url": f"/uploads/{filename}"})
    return files

@router.post("/api/media/delete")
async def delete_media_file(req: Dict[str, str]):
    filename = req.get("filename")
    if not filename: return {"success": False}
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"success": True}
    return {"success": False, "message": "File not found"}

# --- Settings & Menu API (Basic) ---
# A full implementation would parse the complex JSONs. 
# For now, we allow reading/writing the raw Settings table.

from app.models import Setting

@router.get("/api/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    return {row.Setting.key: row.Setting.value for row in result}

@router.post("/api/settings")
async def update_settings(settings: Dict[str, str], db: AsyncSession = Depends(get_db)):
    for key, value in settings.items():
        # Upsert
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting_item = result.scalars().first()
        if setting_item:
            setting_item.value = value
        else:
            db.add(Setting(key=key, value=value))
    await db.commit()
    return {"success": True}

# --- Menu API ---

@router.get("/api/menus")
async def get_menus(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Menu))
    menus = result.scalars().all()
    return [{"name": m.name, "data_json": m.data_json} for m in menus]

@router.post("/api/menus")
async def save_menu(menu: MenuCreate, db: AsyncSession = Depends(get_db)):
    # Upsert
    result = await db.execute(select(Menu).where(Menu.name == menu.name))
    db_menu = result.scalars().first()
    if db_menu:
        db_menu.data_json = menu.data_json
    else:
        new_menu = Menu(name=menu.name, data_json=menu.data_json)
        db.add(new_menu)
    await db.commit()
    return {"success": True}

@router.post("/api/menus/delete")
async def delete_menu(req: Dict[str, str], db: AsyncSession = Depends(get_db)):
    name = req.get("name")
    if not name: return {"success": False}
    result = await db.execute(select(Menu).where(Menu.name == name))
    db_menu = result.scalars().first()
    if db_menu:
        await db.delete(db_menu)
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Not found"}


# --- Banner API ---
from app.models import Banner

@router.get("/api/banners")
async def get_banners(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Banner).order_by(Banner.order_index))
    return res.scalars().all()

@router.post("/api/banners")
async def save_banner(item: BannerCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Banner).where(Banner.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.title = item.title
            obj.subtitle = item.subtitle
            obj.video_url = item.video_url
            obj.image_url = item.image_url
            obj.is_active = item.is_active
            obj.order_index = item.order_index
    else:
        obj = Banner(
            title=item.title, subtitle=item.subtitle, video_url=item.video_url,
            image_url=item.image_url, is_active=item.is_active, order_index=item.order_index
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

@router.post("/api/banners/delete")
async def delete_banner(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Banner).where(Banner.id == req.id))
    await db.commit()
    return {"success": True}

# --- Missions API ---
from app.models import Mission

@router.get("/api/missions")
async def get_missions(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Mission).order_by(Mission.order_index))
    return res.scalars().all()

@router.post("/api/missions")
async def save_mission(item: MissionCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Mission).where(Mission.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.title = item.title
            obj.desc = item.desc
            obj.icon = item.icon
            obj.color = item.color
            obj.order_index = item.order_index
    else:
        obj = Mission(
            title=item.title, desc=item.desc, icon=item.icon,
            color=item.color, order_index=item.order_index
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

# --- Courses API ---
from app.models import Course

@router.get("/api/courses")
async def get_courses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Course).order_by(Course.order_index))
    return res.scalars().all()

@router.post("/api/courses")
async def save_course(item: CourseCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Course).where(Course.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.title_th = item.title_th
            obj.title_en = item.title_en
            obj.video_url = item.video_url
            obj.description = item.description
            obj.color_theme = item.color_theme
            obj.order_index = item.order_index
    else:
        obj = Course(
            title_th=item.title_th, title_en=item.title_en, video_url=item.video_url,
            description=item.description, color_theme=item.color_theme, order_index=item.order_index
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

# --- Stats API ---
from app.models import Statistic

@router.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Statistic).order_by(Statistic.order_index))
    return res.scalars().all()

@router.post("/api/stats")
async def save_stat(item: StatCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Statistic).where(Statistic.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.label = item.label
            obj.value = item.value
            obj.suffix = item.suffix
            obj.icon = item.icon
            obj.order_index = item.order_index
    else:
        obj = Statistic(
            label=item.label, value=item.value, suffix=item.suffix,
            icon=item.icon, order_index=item.order_index
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

# --- Awards API ---
from app.models import Award

@router.get("/api/awards")
async def get_awards(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Award).order_by(Award.order_index))
    return res.scalars().all()

@router.post("/api/awards")
async def save_award(item: AwardCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Award).where(Award.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.title = item.title
            obj.description = item.description
            obj.icon = item.icon
            obj.image_url = item.image_url
            obj.color_theme = item.color_theme or "yellow"
            obj.link_url = item.link_url
            obj.order_index = item.order_index
    else:
        obj = Award(
            title=item.title, description=item.description,
            icon=item.icon, image_url=item.image_url, color_theme=item.color_theme or "yellow",
            link_url=item.link_url, order_index=item.order_index
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

# --- Faculty Management API ---
from app.models import Faculty
from sqlalchemy import delete

@router.get("/api/faculty")
async def get_admin_faculty(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Faculty).order_by(Faculty.id))
    return res.scalars().all()

@router.post("/api/faculty")
async def save_faculty(item: FacultyCreate, db: AsyncSession = Depends(get_db)):
    if item.id:
        res = await db.execute(select(Faculty).where(Faculty.id == item.id))
        obj = res.scalars().first()
        if obj:
            obj.prefix = item.prefix
            obj.fname = item.fname
            obj.lname = item.lname
            obj.fname_en = item.fname_en
            obj.lname_en = item.lname_en
            obj.position = item.position
            obj.email = item.email
            obj.phone = item.phone
            obj.image = item.image
            obj.major = item.major
            obj.admin_position = item.admin_position
            obj.is_expert = item.is_expert
            obj.expertise = item.expertise
    else:
        obj = Faculty(
            prefix=item.prefix, fname=item.fname, lname=item.lname,
            fname_en=item.fname_en, lname_en=item.lname_en, position=item.position,
            email=item.email, phone=item.phone, image=item.image, major=item.major,
            admin_position=item.admin_position, is_expert=item.is_expert, expertise=item.expertise
        )
        db.add(obj)
    await db.commit()
    return {"success": True}

@router.post("/api/faculty/delete")
async def delete_faculty(req: DeleteRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Faculty).where(Faculty.id == req.id))
    await db.commit()
    return {"success": True}

# --- Contact Info API ---
from app.models import ContactInfo

@router.get("/api/contact")
async def get_contact_info(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContactInfo).order_by(ContactInfo.order_index))
    return res.scalars().all()

@router.post("/api/contact")
async def save_contact_info(item: ContactInfoCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContactInfo).where(ContactInfo.key == item.key))
    obj = res.scalars().first()
    if obj:
        obj.value = item.value
        obj.icon = item.icon
        obj.order_index = item.order_index
    else:
        obj = ContactInfo(key=item.key, value=item.value, icon=item.icon, order_index=item.order_index)
        db.add(obj)
    await db.commit()
    return {"success": True}

class ContactDelete(BaseModel):
    key: str

@router.post("/api/contact/delete")
async def delete_contact_info(item: ContactDelete, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ContactInfo).where(ContactInfo.key == item.key))
    await db.commit()
    return {"success": True}
@router.post("/api/generic/delete")
async def generic_delete(req: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    model_name = req.get("model")
    target_id = req.get("id")
    if not model_name or not target_id: return {"success": False}
    
    from app import models
    model_class = getattr(models, model_name, None)
    if model_class:
        await db.execute(delete(model_class).where(model_class.id == target_id))
        await db.commit()
        return {"success": True}
    return {"success": False}


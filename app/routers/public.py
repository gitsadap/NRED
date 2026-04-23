from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import httpx
import json

from app.database import get_db
from app.dependencies import get_global_context
from app.models import Page, News, Activity, Staff
from app.logging_config import logger

router = APIRouter()
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    
    # Fetch Latest News (Limit 6)
    news_res = await db.execute(select(News).order_by(desc(News.created_at)).limit(6))
    news_items = news_res.scalars().all()

    # Fetch Latest Activities (Limit 6)
    act_res = await db.execute(select(Activity).order_by(desc(Activity.created_at)).limit(6))
    activity_items = act_res.scalars().all()

    # Combine
    combined = []
    for n in news_items:
        # Add transient attribute for display logic (handled in template)
        n.display_type = "News"
        combined.append(n)
        
    for a in activity_items:
        a.display_type = "Activity" 
        combined.append(a)
    
    # Sort by date descending
    combined.sort(key=lambda x: x.created_at or x.id, reverse=True)
    
    # Take top 6
    unified_updates = combined[:6]


    # Fetch Banner (Hero)
    from app.models import Banner, Mission, Course, Award, Statistic, ContactInfo
    
    banner_res = await db.execute(select(Banner).where(Banner.is_active == 1).order_by(Banner.order_index))
    banners = banner_res.scalars().all()
    hero_banner = banners[0] if banners else None

    # Fetch Missions
    mission_res = await db.execute(select(Mission).order_by(Mission.order_index))
    mission_items = mission_res.scalars().all()

    # Fetch Courses (Video Grid)
    course_res = await db.execute(select(Course).order_by(Course.order_index))
    courses = course_res.scalars().all()

    # Fetch Awards (Hall of Fame)
    award_res = await db.execute(select(Award).order_by(Award.order_index))
    awards = award_res.scalars().all()

    # Fetch Statistics
    stat_res = await db.execute(select(Statistic).order_by(Statistic.order_index))
    stats = stat_res.scalars().all()



    context["request"] = request
    context["title"] = "หน้าแรก - " + context["site_title"]
    context["is_home"] = True 
    context["unified_updates"] = unified_updates
    
    # Pass dynamic content
    context["hero_banner"] = hero_banner
    context["mission_items"] = mission_items
    context["courses"] = courses
    context["awards"] = awards
    context["stats"] = stats
    context["news"] = news_items

    return templates.TemplateResponse(
        request=request, 
        name="home.html", 
        context=context
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, db: AsyncSession = Depends(get_db)):
    from app.models import Mission, Statistic, Faculty, Award, ContactInfo
    context = await get_global_context(db)

    # Missions / Vision / Values
    mission_res = await db.execute(select(Mission).order_by(Mission.order_index))
    missions = mission_res.scalars().all()

    # Statistics
    stat_res = await db.execute(select(Statistic).order_by(Statistic.order_index))
    stats = stat_res.scalars().all()

    # Faculty members (grouped)
    fac_res = await db.execute(select(Faculty).order_by(Faculty.id))
    faculty_all = fac_res.scalars().all()

    def exec_sort_key(f):
        pos = (f.admin_position or '').strip()
        if 'หัวหน้าภาควิชา' in pos and 'รอง' not in pos:
            return 0  # Head first
        elif 'รองหัวหน้า' in pos:
            return 1  # Deputy heads second
        else:
            return 2  # Others last

    executives = sorted(
        [f for f in faculty_all if f.admin_position],
        key=exec_sort_key
    )
    experts = [f for f in faculty_all if f.is_expert]
    faculty_regular = [f for f in faculty_all if not f.admin_position and not f.is_expert]

    # Awards / Achievements
    award_res = await db.execute(select(Award).order_by(Award.order_index))
    awards = award_res.scalars().all()

    # Contact Info
    contact_res = await db.execute(select(ContactInfo).order_by(ContactInfo.order_index))
    contacts = contact_res.scalars().all()

    context["request"] = request
    context["title"] = "เกี่ยวกับภาควิชา - " + context["site_title"]
    context["missions"] = missions
    context["stats"] = stats
    context["executives"] = executives
    context["experts"] = experts
    context["faculty_regular"] = faculty_regular
    context["faculty_count"] = len(faculty_all)
    context["awards"] = awards
    context["contacts"] = contacts
    return templates.TemplateResponse(request=request, name="about.html", context=context)

@router.get("/links", response_class=HTMLResponse)
async def show_links_directory(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "รวมลิงก์เว็บไซต์ - " + context["site_title"]
    return templates.TemplateResponse(request=request, name="links.html", context=context)

@router.get("/structure", response_class=HTMLResponse)
async def structure_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "โครงสร้างการบริหารงานภาควิชา - " + context["site_title"]
    
    # Fetch executives from Faculty
    from app.models import Faculty
    result = await db.execute(select(Faculty).where(Faculty.admin_position != None).where(Faculty.admin_position != ''))
    rows = result.scalars().all()
    
    executives = []
    for row in rows:
        img_val = row.image or ''
        img = ""
        if img_val:
            if img_val.startswith("http"): img = img_val
            elif img_val.startswith("/static"): img = img_val
            else: img = f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}"
            
        executives.append({
            'id': row.id,
            'prefix': row.prefix or '',
            'fname': row.fname or '',
            'lname': row.lname or '',
            'admin_position': row.admin_position,
            'image': img
        })
        
    # Sort: Head of Department first
    executives.sort(key=lambda x: 0 if x['admin_position'] == 'หัวหน้าภาควิชา' else 1)
    
    context["executives"] = executives
    
    return templates.TemplateResponse(request=request, name="structure.html", context=context)

@router.get("/appeals", response_class=HTMLResponse)
async def appeals_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "ร้องเรียน/อุทธรณ์ - " + context["site_title"]
    # We will need appeals.html
    return templates.TemplateResponse(request=request, name="appeals.html", context=context)



@router.get("/news", response_class=HTMLResponse)
async def show_news(request: Request, category: str = None, tag: str = None, db: AsyncSession = Depends(get_db)):
    from app.models import Tag, Activity
    from datetime import datetime

    context = await get_global_context(db)

    # Fetch Tags for filter
    tag_res = await db.execute(select(Tag).order_by(Tag.name))
    tags = tag_res.scalars().all()

    # Fetch News
    news_query = select(News).order_by(desc(News.created_at))
    if category:
        news_query = news_query.where(News.category == category)
    if tag:
        news_query = news_query.where(News.tags.contains(tag))
    news_result = await db.execute(news_query)
    news_items = news_result.scalars().all()

    # Fetch Activities
    act_query = select(Activity).order_by(desc(Activity.created_at))
    if category:
        act_query = act_query.where(Activity.category == category)
    if tag:
        act_query = act_query.where(Activity.tags.contains(tag))
    act_result = await db.execute(act_query)
    activities = act_result.scalars().all()

    # Fetch Awards (แสดงความยินดี)
    from app.models import Award
    award_items = []
    if not tag and (not category or category == "แสดงความยินดี"):
        aw_query = select(Award).order_by(desc(Award.created_at))
        aw_res = await db.execute(aw_query)
        award_items = aw_res.scalars().all()

    # Merge and sort by created_at
    combined = []
    for n in news_items:
        combined.append({
            "id": n.id, "type": "news",
            "title": n.title, "content": n.content,
            "image_url": n.image_url, "category": n.category,
            "tags": n.tags, "created_at": n.created_at or datetime.min
        })
    for a in activities:
        combined.append({
            "id": a.id, "type": "activity",
            "title": a.title, "content": a.content,
            "image_url": a.image_url, "category": a.category,
            "tags": a.tags, "created_at": a.created_at or datetime.min
        })
    for aw in award_items:
        combined.append({
            "id": aw.id, "type": "award",
            "title": aw.title, "content": aw.description,
            "image_url": aw.image_url, "category": "แสดงความยินดี",
            "tags": "", "created_at": aw.created_at or datetime.min,
            "link_url": getattr(aw, "link_url", None)
        })
    combined.sort(key=lambda x: x["created_at"], reverse=True)

    # Distinct categories from all fetched items
    categories = sorted(set(
        [n.category for n in news_items if n.category] +
        [a.category for a in activities if a.category] +
        (["แสดงความยินดี"] if award_items else [])
    ))

    context["request"] = request
    context["title"] = "ข่าวสารและกิจกรรม - " + context["site_title"]
    context["items"] = combined
    context["tags"] = tags
    context["categories"] = categories
    context["current_category"] = category
    context["current_tag"] = tag
    # keep backward compat
    context["news_list"] = news_items
    return templates.TemplateResponse(request=request, name="news.html", context=context)


@router.get("/news/{id}", response_class=HTMLResponse)
async def show_news_detail(id: int, request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    result = await db.execute(select(News).where(News.id == id))
    news_item = result.scalars().first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    
    context["request"] = request
    context["title"] = news_item.title + " - " + context["site_title"]
    context["news"] = news_item
    return templates.TemplateResponse(request=request, name="news_single.html", context=context)

@router.get("/activities", response_class=HTMLResponse)
async def show_activities(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    result = await db.execute(select(Activity).order_by(desc(Activity.created_at)))
    activities_list = result.scalars().all()
    
    context["request"] = request
    context["title"] = "กิจกรรมและโครงการ - " + context["site_title"]
    context["activities"] = activities_list
    return templates.TemplateResponse(request=request, name="activities.html", context=context)

@router.get("/activities/{id}", response_class=HTMLResponse)
async def show_activity_detail(id: int, request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    result = await db.execute(select(Activity).where(Activity.id == id))
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    context["request"] = request
    context["title"] = activity.title + " - " + context["site_title"]
    context["activity"] = activity
    return templates.TemplateResponse(request=request, name="activity_single.html", context=context)

from app.models import Staff

import asyncpg


from app.models import Faculty, FacultyCV


@router.get("/faculty", response_class=HTMLResponse)
async def show_faculty(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    
    # Fetch all CVs locally
    cv_res = await db.execute(select(FacultyCV))
    cv_map = {cv.user_id: cv.cv_file for cv in cv_res.scalars().all()}
    
    faculty_groups = []
    
    try:
        # Fetch Faculty from DB
        result = await db.execute(select(Faculty).order_by(Faculty.id))
        faculty_rows = result.scalars().all()
        
        # Helper to calculate position weight
        def get_position_weight(person):
            # Check position string for keywords
            pos = (person.position or "").strip()
            prefix = (person.prefix or "").strip()
            text = f"{pos} {prefix}"
            
            if "ศาสตราจารย์" in text and "รอง" not in text and "ผู้ช่วย" not in text:
                return 5 # Professor
            if "รองศาสตราจารย์" in text:
                return 4 # Assoc Prof
            if "ผู้ช่วยศาสตราจารย์" in text:
                return 3 # Asst Prof
            if "อาจารย์" in text:
                return 2 # Lecturer
            return 1 # Other

        # Process all rows into a list of dicts with calculated weight
        all_faculty = []
        for row in faculty_rows:
            # Name Logic
            prefix = row.prefix or ''
            fname = row.fname
            lname = row.lname
            display_name = f"{prefix} {fname} {lname}".strip()
            
            fname_en = row.fname_en or ''
            lname_en = row.lname_en or ''
            
            display_name_en = ""
            if fname_en or lname_en:
                 prefix_en = ""
                 if prefix and "ดร." in prefix: prefix_en = "Dr."
                 elif prefix and "นาย" in prefix: prefix_en = "Mr."
                 elif prefix and "นางสาว" in prefix: prefix_en = "Ms."
                 elif prefix and "นาง" in prefix: prefix_en = "Mrs."
                 elif prefix and "ผศ." in prefix: prefix_en = "Asst. Prof."
                 elif prefix and "รศ." in prefix: prefix_en = "Assoc. Prof."
                 elif prefix and "ศ." in prefix: prefix_en = "Prof."
                 
                 display_name_en = f"{prefix_en} {fname_en} {lname_en}".strip()

            # Image Logic
            img_val = row.image or ''
            img = ""
            if img_val:
                if img_val.startswith("http"): img = img_val
                elif img_val.startswith("/static"): img = img_val
                else: img = f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}"
            
            cv_filename = cv_map.get(row.id)
            cv_url = None
            if cv_filename:
                # To handle both old uploads (filename only) and new uploads (/uploads/... format)
                if cv_filename.startswith("/uploads/"):
                    cv_url = cv_filename
                else:
                    cv_url = f"/uploads/{cv_filename}"
            
            # Expertise Logic
            expertise = []
            if row.expertise:
                if isinstance(row.expertise, list):
                    expertise = row.expertise
                elif isinstance(row.expertise, dict):
                    expertise = [str(row.expertise)]
                else:
                    try:
                        loaded = json.loads(row.expertise)
                        if isinstance(loaded, list):
                            expertise = loaded
                        else:
                             expertise = [str(loaded)]
                    except:
                        # Treat as simple string split by newline or comma if needed, or just single item
                        expertise = [row.expertise]

            major_val = row.major
            if major_val == 'ภูมิศาสตร์':
                major_val = 'ภูมิศาสตร์และภูมิสารสนเทศศาสตร์'

            all_faculty.append({
                'id': row.id,
                'prefix': prefix,
                'fname': fname,
                'lname': lname,
                'name': display_name,
                'name_en': display_name_en,
                'position': row.position or '-',
                'email': row.email or '-',
                'phone': row.phone or '-',
                'image': img, 
                'cv_url': cv_url,
                'major': major_val,
                'admin_position': row.admin_position,
                'is_expert': row.is_expert,
                'expertise': expertise,
                '_weight': get_position_weight(row)
            })


        # Separate Executives and Experts
        executives = [f for f in all_faculty if f.get('admin_position') and f['admin_position'].strip()]
        experts = [f for f in all_faculty if f['is_expert'] and not (f.get('admin_position') and f['admin_position'].strip())]
        
        others = []
        for f in all_faculty:
            f_copy = dict(f)
            f_copy['admin_position'] = None
            others.append(f_copy)
        
        # Sort Executives
        # Head > Deputy
        executives.sort(key=lambda x: 0 if x['admin_position'] and 'หัวหน้าภาควิชา' in x['admin_position'] and 'รอง' not in x['admin_position'] else 1)
        
        if executives:
             faculty_groups.append({
                "name": "ผู้บริหารภาควิชา",
                "members": executives
            })

        # Sort Experts
        experts.sort(key=lambda x: x['_weight'], reverse=True)
        
        if experts:
            faculty_groups.append({
                "name": "ผู้ทรงคุณวุฒิพิเศษ / ผู้เชี่ยวชาญ",
                "members": experts
            })
            
        # Group Others by Major
        # Get unique majors
        majors = set(f['major'] for f in others if f['major'])
            
        # Sort majors alphabetically, but push specific ones to the end
        def major_sort_key(m):
            if m == 'บุคลากรสายสนับสนุน': return (2, m)
            return (0, m)
        sorted_majors = sorted(list(majors), key=major_sort_key)
        
        for m in sorted_majors:
            group_members = [f for f in others if f['major'] == m]
            
            if group_members:
                # Sort by weight desc, then name asc
                group_members.sort(key=lambda x: (-x['_weight'], x['fname']))
                faculty_groups.append({
                    "name": m,
                    "members": group_members
                })

    except Exception as e:
        logger.error(f"Error fetching faculty groups: {e}", exc_info=True)
        context["error"] = "ขออภัย ระบบไม่สามารถโหลดข้อมูลบุคลากรได้ในขณะนี้"

    context["request"] = request
    context["title"] = "คณาจารย์ - " + context["site_title"]
    context["heading"] = "คณาจารย์"
    context["description"] = "บุคลากรผู้ทรงคุณวุฒิแห่งภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม"
    context["faculty_groups"] = faculty_groups
    return templates.TemplateResponse(request=request, name="faculty.html", context=context)


@router.get("/teacher-portal", response_class=HTMLResponse)
async def teacher_portal():
    # Deprecated insecure flow (public upload without auth) was removed.
    # Teachers should login and use the CV update section in the Admin/Teacher dashboard.
    return RedirectResponse(url="/admin/login", status_code=302)

@router.get("/executives", response_class=HTMLResponse)
async def show_executives(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    
    # Needs a combined list mapping similar to /faculty but filtering just executives
    result = await db.execute(select(Faculty).where(Faculty.admin_position != None).where(Faculty.admin_position != ''))
    faculty_rows = result.scalars().all()
    
    faculty_list = []
    for row in faculty_rows:
        img_val = row.image or ''
        img = ""
        if img_val:
            if img_val.startswith("http"): img = img_val
            elif img_val.startswith("/static"): img = img_val
            else: img = f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}"
            
        faculty_list.append({
            'id': row.id,
            'prefix': row.prefix or '',
            'fname': row.fname or '',
            'lname': row.lname or '',
            'admin_position': row.admin_position,
            'position': row.position or '-',
            'email': row.email or '-',
            'phone': row.phone or '-',
            'image': img
        })
        
    faculty_list.sort(key=lambda x: 0 if x['admin_position'] and 'หัวหน้าภาควิชา' in x['admin_position'] and 'รอง' not in x['admin_position'] else 1)
    
    context["request"] = request
    context["title"] = "ผู้บริหาร - " + context["site_title"]
    context["heading"] = "ผู้บริหาร"
    context["description"] = "คณะผู้บริหารภาควิชาฯ"
    # To use the same faculty.html, we pass them as a group
    context["faculty_groups"] = [{"name": "ผู้บริหาร", "members": faculty_list}]
    return templates.TemplateResponse(request=request, name="faculty.html", context=context)

@router.get("/support-staff", response_class=HTMLResponse)
async def show_support_staff(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    result = await db.execute(select(Faculty).where(Faculty.major == 'บุคลากรสายสนับสนุน'))
    faculty_rows = result.scalars().all()
    
    faculty_list = []
    for row in faculty_rows:
        img_val = row.image or ''
        img = ""
        if img_val:
            if img_val.startswith("http"): img = img_val
            elif img_val.startswith("/static"): img = img_val
            else: img = f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}"
            
        faculty_list.append({
            'id': row.id,
            'prefix': row.prefix or '',
            'fname': row.fname or '',
            'lname': row.lname or '',
            'position': row.position or '-',
            'email': row.email or '-',
            'phone': row.phone or '-',
            'image': img
        })
    
    context["request"] = request
    context["title"] = "บุคลากรสายสนับสนุน - " + context["site_title"]
    context["heading"] = "บุคลากรสายสนับสนุน"
    context["description"] = "ทีมงานสนับสนุนการเรียนการสอนและการบริหาร"
    context["faculty_groups"] = [{"name": "บุคลากรสายสนับสนุน", "members": faculty_list}]
    return templates.TemplateResponse(request=request, name="faculty.html", context=context)

@router.get("/curriculum", response_class=HTMLResponse)
async def curriculum_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "หลักสูตรทั้งหมด - " + context["site_title"]
    return templates.TemplateResponse(request=request, name="curriculum.html", context=context)

@router.get("/research", response_class=HTMLResponse)
async def research_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "ผลงานวิจัย - " + context["site_title"]
    context["heading"] = "ผลงานวิจัย"
    context["description"] = "ผลงานตีพิมพ์ทางวิชาการและงานวิจัยของคณาจารย์จากฐานข้อมูล Google Scholar"
    return templates.TemplateResponse(request=request, name="research.html", context=context)

@router.get("/current-students", response_class=HTMLResponse)
async def current_students_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "นิสิตปัจจุบัน - " + context["site_title"]
    context["heading"] = "นิสิตปัจจุบัน"
    context["description"] = "ข้อมูลและบริการสำหรับนิสิตภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม"
    return templates.TemplateResponse(request=request, name="current_students.html", context=context)


@router.get("/services", response_class=HTMLResponse)
async def services_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "บริการออนไลน์ (E-Services) - " + context["site_title"]
    context["heading"] = "บริการและระบบสารสนเทศ (E-Services)"
    context["description"] = "รวมระบบสารสนเทศ เมนูลัด และบริการออนไลน์สำหรับนิสิต บุคลากร และบุคคลทั่วไป"
    return templates.TemplateResponse(request=request, name="services.html", context=context)


@router.get("/coop", response_class=HTMLResponse)
async def coop_education_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_global_context(db)
    context["request"] = request
    context["title"] = "สหกิจศึกษา - " + context["site_title"]
    context["heading"] = "สหกิจศึกษา"
    context["description"] = "ข้อมูลเกี่ยวกับการปฏิบัติงานสหกิจศึกษา และการฝึกประสบการณ์วิชาชีพ"
    return templates.TemplateResponse(request=request, name="coop.html", context=context)


@router.get("/page-raw/{slug}", response_class=HTMLResponse)
async def show_page_raw(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Return raw HTML content for a page - used by iframe in page.html to avoid srcdoc escaping issues."""
    result = await db.execute(select(Page).where(Page.slug == slug, Page.is_published == 1))
    page = result.scalars().first()
    
    if not page or not page.content:
        raise HTTPException(status_code=404, detail="Page not found")
        
    content = page.content or ''
    
    # 💡 [TRICK] ค้นหาและแทนที่คลาส Sarabun ให้กลายเป็น font-sans อัตโนมัติ
    content = content.replace("font-['Sarabun',sans-serif]", "font-sans")
    
    # If it's already a full HTML document, return as-is
    stripped = content.strip()
    if stripped.lower().startswith('<!doctype') or stripped.lower().startswith('<html'):
        return HTMLResponse(content=content)
        
    # 💡 [FIXED] จัดโครงสร้าง HTML ให้แท็ก <meta> และ <link> เข้าไปอยู่ใน <head>
    wrapped = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Kanit', 'sans-serif']
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Kanit', sans-serif; background-color: transparent; }}
    </style>
</head>
<body>
    {content}
</body>
</html>"""
    return HTMLResponse(content=wrapped)

@router.get("/{slug}", response_class=HTMLResponse)
async def show_page(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    # Skip assets/uploads strings if they accidentally get here (though StaticFiles should catch them if valid)
    if slug in ["assets", "uploads", "favicon.ico"]:
        raise HTTPException(status_code=404)

    context = await get_global_context(db)
    
    # Query Page
    result = await db.execute(select(Page).where(Page.slug == slug, Page.is_published == 1))
    page = result.scalars().first()
    
    if not page:
        # 404
        # return templates.TemplateResponse("404.html", context, status_code=404)
        raise HTTPException(status_code=404, detail="Page not found")

    context["request"] = request
    context["title"] = page.title + " - " + context["site_title"]
    context["page"] = page
    
    template_name = "page.html"
    if page.template and page.template != "page":
         # Fallback check if template exists
         # For now default to page.html
         pass

    return templates.TemplateResponse(request=request, name=template_name, context=context)

@router.get("/api/curriculum-stats-proxy")
async def get_curriculum_stats_proxy():
    api_url = "https://oassar.agi.nu.ac.th/esprel/vendor/include/info.php"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(api_url)
            # ตรวจสอบว่าได้ข้อมูลถูกต้องไหม
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Curriculum stats proxy upstream error: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail="Upstream API unavailable")
        except Exception as e:
            logger.error(f"Curriculum stats proxy failed: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail="Upstream API unavailable")

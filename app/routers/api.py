from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
import json

from app.database import get_db
from app.dependencies import get_global_context
from app.models import Page, News, Activity, Staff, Faculty, FacultyCV, Banner, Mission, Course, Award, Statistic, ContactInfo, Setting

router = APIRouter(prefix="/api/v1", tags=["Public API"])

@router.get("/context")
async def api_global_context(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลการตั้งค่า, เมนู, และ Footer ที่ใช้ร่วมกันทุกหน้า"""
    context = await get_global_context(db)
    
    # Remove large unneeded objects from context to make it pure JSON
    if "request" in context:
         del context["request"]
    
    return {"status": "success", "data": context}

@router.get("/home")
async def api_home(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลทั้งหมดสำหรับแสดงผลหน้ากแรก"""
    # Latest News & Activities
    news_res = await db.execute(select(News).order_by(desc(News.created_at)).limit(6))
    act_res = await db.execute(select(Activity).order_by(desc(Activity.created_at)).limit(6))
    
    news_items = [{"id": n.id, "title": n.title, "image": n.image_url, "created_at": n.created_at, "type": "News"} for n in news_res.scalars().all()]
    activity_items = [{"id": a.id, "title": a.title, "image": a.image_url, "created_at": a.created_at, "type": "Activity"} for a in act_res.scalars().all()]
    
    combined = sorted(news_items + activity_items, key=lambda x: x["created_at"] or getattr(x, 'id', 0), reverse=True)[:6]
    
    # Banners
    banner_res = await db.execute(select(Banner).where(Banner.is_active == 1).order_by(Banner.order_index))
    banners = [{"id": b.id, "title": b.title, "subtitle": b.subtitle, "image_url": b.image_url, "video_url": b.video_url} for b in banner_res.scalars().all()]
    
    # Missions
    mission_res = await db.execute(select(Mission).order_by(Mission.order_index))
    missions = [{"id": m.id, "title": m.title, "description": m.desc, "icon": m.icon, "color": m.color} for m in mission_res.scalars().all()]
    
    # Courses
    course_res = await db.execute(select(Course).order_by(Course.order_index))
    courses = [{"id": c.id, "name_th": c.title_th, "name_en": c.title_en, "youtube_url": c.video_url} for c in course_res.scalars().all()]
    
    # Awards
    award_res = await db.execute(select(Award).order_by(Award.order_index))
    awards = [{"id": a.id, "title": a.title, "description": a.description, "recipient": getattr(a, 'recipient', ''), "image_url": a.image_url, "icon": a.icon, "link_url": a.link_url} for a in award_res.scalars().all()]
    
    # Stats
    stat_res = await db.execute(select(Statistic).order_by(Statistic.order_index))
    stats = [{"label": s.label, "number": s.value, "suffix": s.suffix, "icon": s.icon} for s in stat_res.scalars().all()]

    # Fetch Settings for quick buttons fallback
    result = await db.execute(select(Setting))
    settings_dict = {row.Setting.key: row.Setting.value for row in result.all()}
    
    quick_buttons = json.loads(settings_dict.get('quick_buttons_json') or '[]')
    if not quick_buttons:
        quick_buttons = [
            {'title': 'Natural Resources & Environment', 'url': '/curriculum#nre', 'color': 'blue', 'image': ''},
            {'title': 'Environmental Science', 'url': '/curriculum#envi', 'color': 'teal', 'image': ''},
            {'title': 'Geography', 'url': '/curriculum#geo', 'color': 'indigo', 'image': ''}
        ]

    # If DB stats empty, use fallback from settings or defaults
    if not stats:
        stats_json = settings_dict.get('stats_json')
        if stats_json:
            stats = json.loads(stats_json)
        else:
            stats = [
                {'number': '22', 'label': 'หลักสูตร', 'icon': 'graduation-cap'},
                {'number': '1424', 'label': 'นิสิตปัจจุบัน', 'icon': 'id-card'}
            ]

    return {
        "status": "success",
        "data": {
            "updates": combined,
            "banners": banners,
            "missions": missions,
            "courses": courses,
            "awards": awards,
            "quick_buttons": quick_buttons,
            "stats": stats
        }
    }

@router.get("/news")
async def api_news_list(category: str = None, db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลรายการข่าวสาร"""
    query = select(News).order_by(desc(News.created_at))
    if category:
        query = query.where(News.category == category)
        
    result = await db.execute(query)
    news_list = result.scalars().all()
    
    return {"status": "success", "data": news_list}

@router.get("/news/{id}")
async def api_news_detail(id: int, db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลข่าวสารตาม ID"""
    result = await db.execute(select(News).where(News.id == id))
    news_item = result.scalars().first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    return {"status": "success", "data": news_item}

@router.get("/activities")
async def api_activities_list(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลรายการกิจกรรม"""
    result = await db.execute(select(Activity).order_by(desc(Activity.created_at)))
    activities_list = result.scalars().all()
    return {"status": "success", "data": activities_list}

@router.get("/activities/{id}")
async def api_activity_detail(id: int, db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลกิจกรรมตาม ID"""
    result = await db.execute(select(Activity).where(Activity.id == id))
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return {"status": "success", "data": activity}

@router.get("/faculty")
async def api_faculty_list(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลคณาจารย์ พร้อมจัดกลุ่ม"""
    cv_res = await db.execute(select(FacultyCV))
    cv_map = {cv.user_id: cv.cv_file for cv in cv_res.scalars().all()}
    
    result = await db.execute(select(Faculty).order_by(Faculty.id))
    faculty_rows = result.scalars().all()
    
    def get_position_weight(person):
        pos = (person.position or "").strip()
        prefix = (person.prefix or "").strip()
        text = f"{pos} {prefix}"
        if "ศาสตราจารย์" in text and "รอง" not in text and "ผู้ช่วย" not in text: return 5
        if "รองศาสตราจารย์" in text: return 4
        if "ผู้ช่วยศาสตราจารย์" in text: return 3
        if "อาจารย์" in text: return 2
        return 1

    all_faculty = []
    for row in faculty_rows:
        img_val = row.image or ''
        img = img_val if img_val.startswith(("http", "/static")) else (f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}" if img_val else "")
        cv_url = f"/uploads/{cv_map[row.id]}" if row.id in cv_map else None
        
        expertise = []
        if row.expertise:
            try:
                loaded = json.loads(row.expertise) if isinstance(row.expertise, str) else row.expertise
                expertise = loaded if isinstance(loaded, list) else [str(loaded)]
            except:
                expertise = [row.expertise]

        all_faculty.append({
            'id': row.id,
            'prefix': row.prefix or '',
            'fname': row.fname,
            'lname': row.lname,
            'position': row.position or '-',
            'email': row.email or '-',
            'phone': row.phone or '-',
            'image': img, 
            'cv_url': cv_url,
            'major': 'ภูมิศาสตร์และภูมิสารสนเทศศาสตร์' if row.major == 'ภูมิศาสตร์' else row.major,
            'admin_position': row.admin_position,
            'is_expert': row.is_expert,
            'expertise': expertise,
            '_weight': get_position_weight(row)
        })

    executives = sorted([f for f in all_faculty if f.get('admin_position') and f['admin_position'].strip()], key=lambda x: 0 if x['admin_position'] and 'หัวหน้าภาควิชา' in x['admin_position'] and 'รอง' not in x['admin_position'] else 1)
    experts = sorted([f for f in all_faculty if f['is_expert'] and not (f.get('admin_position') and f['admin_position'].strip())], key=lambda x: x['_weight'], reverse=True)
    others = [f for f in all_faculty]
    
    # Process others group similarly to SSR logic...
    # (Simplified for JSON response, frontend can group or backend groups here)
    faculty_groups = []
    if executives: faculty_groups.append({"name": "ผู้บริหารภาควิชา", "members": executives})
    if experts: faculty_groups.append({"name": "ผู้ทรงคุณวุฒิพิเศษ / ผู้เชี่ยวชาญ", "members": experts})
    
    majors = set(f['major'] for f in others if f['major'])
    sorted_majors = sorted(list(majors), key=lambda m: (2, m) if m == 'บุคลากรสายสนับสนุน' else (0, m))
    
    for m in sorted_majors:
        members = [f for f in others if f['major'] == m]
        if members:
            members.sort(key=lambda x: (-x['_weight'], x['fname']))
            faculty_groups.append({"name": m, "members": members})
            
    return {"status": "success", "data": faculty_groups}

@router.get("/staff/{type}")
async def api_staff(type: str, db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลสายสนับสนุน หรือ ผู้บริหาร"""
    result = await db.execute(select(Staff).where(Staff.type == type).order_by(Staff.order_index))
    return {"status": "success", "data": result.scalars().all()}

@router.get("/pages/{slug}")
async def api_page(slug: str, db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลเนื้อหาจากหน้า Dynamic (เช่น about, curriculum)"""
    result = await db.execute(select(Page).where(Page.slug == slug, Page.is_published == 1))
    page = result.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"status": "success", "data": page}


@router.get("/external-stats")
async def api_external_stats(db: AsyncSession = Depends(get_db)):
    """Fetch external stats aggregated directly from MSSQL database + local Postgres counts for Faculty and Staff"""
    import pymssql
    import asyncio
    
    def fetch_mssql_stats():
        query = """
        SELECT 
            TRIM(LEVGROUPNAME) AS level,
            TRIM(PROGRAMNAME) AS program,
            SUM(CASE WHEN STDSTATUSNAME LIKE '%สำเร็จ%' THEN 1 ELSE 0 END) AS graduated,
            SUM(CASE WHEN STDSTATUSNAME LIKE '%พ้นสภาพ%' OR STDSTATUSNAME LIKE '%ลาออก%' OR STDSTATUSNAME LIKE '%คัดชื่อ%' THEN 1 ELSE 0 END) AS lost,
            SUM(CASE WHEN STDSTATUSNAME NOT LIKE '%สำเร็จ%' AND STDSTATUSNAME NOT LIKE '%พ้นสภาพ%' AND STDSTATUSNAME NOT LIKE '%ลาออก%' AND STDSTATUSNAME NOT LIKE '%คัดชื่อ%' THEN 1 ELSE 0 END) AS active
        FROM [Agri].[View_Student4AgriFaculty]
        WHERE (
            (LEVGROUPNAME = 'ปริญญาตรี' AND (PROGRAMNAME LIKE '%สิ่งแวดล้อม%' OR PROGRAMNAME LIKE '%ภูมิ%'))
            OR 
            (LEVGROUPNAME IN ('ปริญญาโท', 'ปริญญาเอก') AND (
                PROGRAMNAME LIKE '%การจัดการสิ่งแวดล้อม%' OR 
                PROGRAMNAME LIKE '%ทรัพยากรธรรมชาติ%' OR 
                PROGRAMNAME LIKE '%วิทยาศาสตร์สิ่งแวดล้อม%' OR 
                PROGRAMNAME LIKE '%ภูมิสารสนเทศ%'
            ))
        )
        GROUP BY LEVGROUPNAME, PROGRAMNAME
        ORDER BY LEVGROUPNAME DESC, PROGRAMNAME ASC
        """
        
        import os
        conn = pymssql.connect(
            server=os.getenv("MSSQL_SERVER", "10.10.98.203"),
            user=os.getenv("MSSQL_USER", "AGRI_Teeradety"),
            password=os.getenv("MSSQL_PASSWORD", ""),
            database=os.getenv("MSSQL_DATABASE", "NUDB"),
            login_timeout=10
        )
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    try:
        # Run synchronous pymssql query in a thread to prevent blocking FastAPI's async event loop
        rows = await asyncio.to_thread(fetch_mssql_stats)
        
        # Parallel fetch for Faculty directly from local Postgres via SQLAlchemy
        from sqlalchemy import func
        faculty_count_stmt = select(func.count()).select_from(Faculty)
        
        faculty_count_res = await db.execute(faculty_count_stmt)
        total_faculty = faculty_count_res.scalar() or 0
        
        summary = {}
        grand_total = {'graduated': 0, 'lost': 0, 'active': 0}
        
        for row in rows:
            level = row['level']
            program = row['program']
            
            if level not in summary:
                summary[level] = {'programs': {}}
            
            summary[level]['programs'][program] = {
                'graduated': row['graduated'],
                'lost': row['lost'],
                'active': row['active']
            }
            
            grand_total['graduated'] += row['graduated']
            grand_total['lost'] += row['lost']
            grand_total['active'] += row['active']
            
        result = {
            'status': 'success',
            'analysis_overview': {
                'grand_total': grand_total['graduated'] + grand_total['lost'] + grand_total['active'],
                'total_graduated': grand_total['graduated'],
                'total_lost': grand_total['lost'],
                'total_active': grand_total['active'],
                'total_faculty': total_faculty
            },
            'data_summary': summary,
            'results': {} 
        }
        
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/research")
async def api_research_list(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลงานวิจัยทั้งหมด (SerpApi Organic Results) เรียงตามอาจารย์"""
    result = await db.execute(select(Faculty).where(Faculty.scholar_data != None).order_by(Faculty.id))
    faculty_rows = result.scalars().all()
    
    research_data = []
    for row in faculty_rows:
        img_val = row.image or ''
        img = img_val if img_val.startswith(("http", "/static", "data:")) else (f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}" if img_val else "")
        
        scholar_results = []
        if row.scholar_data:
            try:
                loaded = json.loads(row.scholar_data) if isinstance(row.scholar_data, str) else row.scholar_data
                scholar_results = loaded if isinstance(loaded, list) else []
            except Exception:
                pass
                
        metrics = {}
        if row.cited:
            try:
                metrics = json.loads(row.cited) if isinstance(row.cited, str) else row.cited
            except Exception:
                pass
                
        if not scholar_results and not metrics:
            continue
            
        research_data.append({
            'faculty_id': row.id,
            'name_th': f"{row.prefix or ''} {row.fname} {row.lname}".strip(),
            'name_en': f"{row.fname_en or ''} {row.lname_en or ''}".strip(),
            'image': img,
            'scholar_id': row.scholar_id,
            'publications': scholar_results,
            'metrics': metrics
        })
        
    return {"status": "success", "data": research_data}
@router.get("/coop-stats")
async def get_coop_stats(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลสถิติสหกิจศึกษาจากตาราง coop_students และ coop_companies โดยระบุ schema เป็น public"""
    try:
        total_std = await db.scalar(text("SELECT COUNT(*) FROM public.coop_students"))
        total_comp = await db.scalar(text("SELECT COUNT(DISTINCT co_code) FROM public.coop_students WHERE co_code IS NOT NULL"))

        majors_rows = await db.execute(text("SELECT major, COUNT(*) as cnt FROM public.coop_students GROUP BY major"))
        majors_data = []
        for row in majors_rows:
            m_name = "ทรัพยากรธรรมชาติและสิ่งแวดล้อม" if row.major == 1 else "ภูมิศาสตร์" if row.major == 2 else "อื่นๆ"
            majors_data.append({"name": m_name, "count": row.cnt})

        # Top 10 บริษัท ของ ทรัพยากรธรรมชาติและสิ่งแวดล้อม (major = 1)
        top_nre_rows = await db.execute(text("""
            SELECT c.company_name, COUNT(s.id) as cnt
            FROM public.coop_students s
            JOIN public.coop_companies c ON s.co_code = c.co_code
            WHERE s.major = 1
            GROUP BY c.company_name ORDER BY cnt DESC LIMIT 10
        """))
        top_nre = [{"name": r.company_name, "count": r.cnt} for r in top_nre_rows]

        # Top 10 บริษัท ของ ภูมิศาสตร์ (major = 2)
        top_geo_rows = await db.execute(text("""
            SELECT c.company_name, COUNT(s.id) as cnt
            FROM public.coop_students s
            JOIN public.coop_companies c ON s.co_code = c.co_code
            WHERE s.major = 2
            GROUP BY c.company_name ORDER BY cnt DESC LIMIT 10
        """))
        top_geo = [{"name": r.company_name, "count": r.cnt} for r in top_geo_rows]

        # ดึงรายชื่อบริษัททั้งหมดสำหรับสร้างตาราง
        all_comp_rows = await db.execute(text("SELECT co_code, company_name, address, phone FROM public.coop_companies ORDER BY co_code"))
        all_companies = [{"id": r.co_code, "name": r.company_name, "address": r.address or "-", "phone": r.phone or "-"} for r in all_comp_rows]

        loc_rows = await db.execute(text("""
            SELECT c.company_name, c.lat, c.long, s.name, s.major
            FROM public.coop_students s
            JOIN public.coop_companies c ON s.co_code = c.co_code
            WHERE c.lat IS NOT NULL AND c.long IS NOT NULL
        """))
        locations = []
        for r in loc_rows:
            m_name = "ทรัพยากรธรรมชาติและสิ่งแวดล้อม" if r.major == 1 else "ภูมิศาสตร์"
            locations.append({
                "company": r.company_name, "name": r.name, "major": m_name, 
                "lat": float(r.lat), "long": float(r.long), "major_id": r.major
            })

        return {
            "status": "success",
            "data": {
                "summary": {"total_students": total_std or 0, "total_companies": total_comp or 0},
                "majors": majors_data,
                "top_nre": top_nre,
                "top_geo": top_geo,
                "all_companies": all_companies,
                "locations": locations
            }
        }
    except Exception as e:
        print(f"❌ [COOP-STATS ERROR]: {str(e)}")
        return {"status": "error", "message": str(e)}
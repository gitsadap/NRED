
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func
import json
import re
import httpx
from app.database import get_db
from app.dependencies import get_global_context
from app.models import Page, News, Activity, Staff, Faculty, FacultyCV, Banner, Mission, Course, Award, Statistic, ContactInfo
from app.logging_config import logger

router = APIRouter(prefix="/api/v1", tags=["Public API"])

@router.get("/context")
async def api_global_context(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลการตั้งค่า, เมนู, และ Footer ที่ใช้ร่วมกันทุกหน้า"""
    context = await get_global_context(db)
    
    
    if "request" in context:
         del context["request"]
    
    return {"status": "success", "data": context}

@router.get("/home")
async def api_home(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลทั้งหมดสำหรับแสดงผลหน้ากแรก"""
    
    news_res = await db.execute(select(News).order_by(desc(News.created_at)).limit(6))
    act_res = await db.execute(select(Activity).order_by(desc(Activity.created_at)).limit(6))
    
    news_items = [{"id": n.id, "title": n.title, "image": n.image_url, "created_at": n.created_at, "type": "News"} for n in news_res.scalars().all()]
    activity_items = [{"id": a.id, "title": a.title, "image": a.image_url, "created_at": a.created_at, "type": "Activity"} for a in act_res.scalars().all()]
    
    combined = sorted(news_items + activity_items, key=lambda x: x["created_at"] or getattr(x, 'id', 0), reverse=True)[:6]
    
    
    banner_res = await db.execute(select(Banner).where(Banner.is_active == 1).order_by(Banner.order_index))
    banners = [{"id": b.id, "title": b.title, "subtitle": b.subtitle, "image_url": b.image_url, "video_url": b.video_url} for b in banner_res.scalars().all()]
    
    
    mission_res = await db.execute(select(Mission).order_by(Mission.order_index))
    missions = [{"id": m.id, "title": m.title, "description": m.desc, "icon": m.icon, "color": m.color} for m in mission_res.scalars().all()]
    
    
    course_res = await db.execute(select(Course).order_by(Course.order_index))
    courses = [{"id": c.id, "name_th": c.title_th, "name_en": c.title_en, "youtube_url": c.video_url} for c in course_res.scalars().all()]
    
    
    award_res = await db.execute(select(Award).order_by(Award.order_index))
    awards = [{"id": a.id, "title": a.title, "description": a.description, "recipient": getattr(a, 'recipient', ''), "image_url": a.image_url, "icon": a.icon, "link_url": a.link_url} for a in award_res.scalars().all()]
    
    
    stat_res = await db.execute(select(Statistic).order_by(Statistic.order_index))
    stats = [{"label": s.label, "number": s.value, "suffix": s.suffix, "icon": s.icon} for s in stat_res.scalars().all()]

    context = await get_global_context(db)
    settings_dict = context.get("settings", {})

    quick_buttons = context.get("quick_buttons", [])
    if not quick_buttons:
        quick_buttons = [
            {'title': 'Natural Resources & Environment', 'url': '/curriculum#nre', 'color': 'blue', 'image': ''},
            {'title': 'Environmental Science', 'url': '/curriculum#envi', 'color': 'teal', 'image': ''},
            {'title': 'Geography', 'url': '/curriculum#geo', 'color': 'indigo', 'image': ''}
        ]

    
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
        img = img_val if img_val.startswith(("http", "/static", "/uploads")) else (f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}" if img_val else "")
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
    """Fetch student stats directly from SQL Server Database + local Postgres counts for Faculty"""
    import os
    import pymssql
    
    try:
        
        faculty_count_stmt = select(func.count()).select_from(Faculty)
        faculty_count_res = await db.execute(faculty_count_stmt)
        total_faculty = faculty_count_res.scalar() or 0

        
        total_research = 0
        research_res = await db.execute(select(Faculty.scholar_data).where(Faculty.scholar_data != None))
        for s_data in research_res.scalars().all():
            if s_data:
                try:
                    loaded = json.loads(s_data) if isinstance(s_data, str) else s_data
                    if isinstance(loaded, list):
                        total_research += len(loaded)
                except Exception:
                    pass

        
        conn = pymssql.connect(
            server=os.getenv('STUDENT_DB_SERVER'),
            user=os.getenv('STUDENT_DB_USER'),
            password=os.getenv('STUDENT_DB_PASS'),
            database=os.getenv('STUDENT_DB_NAME')
        )
        cursor = conn.cursor(as_dict=True)
        
        sql = """
        SELECT 
            LEVGROUPNAME as level, 
            PROGRAMNAME as program, 
            STDSTATUSID as status_id,
            COUNT(*) as count
        FROM [Agri].[View_Student4AgriFaculty]
        GROUP BY LEVGROUPNAME, PROGRAMNAME, STDSTATUSID
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        data_summary = {}
        grand_total = 0
        total_active = 0
        total_graduated = 0
        total_lost = 0
        
        active_ids = {10, 11, 12}
        graduated_ids = {40}
        lost_ids = {21, 22, 50, 51, 52, 60}
        
        from app.routers.dashboard_api import decode_thai
        
        for row in rows:
            level = decode_thai(row['level'])
            program = decode_thai(row['program'])
            
            
            if not any(k in program for k in ['สิ่งแวดล้อม', 'ภูมิศาสตร์', 'ภูมิสารสนเทศ', 'อวกาศ', 'ทรัพยากรธรรมชาติ']):
                continue
            if 'วิทยาศาสตร์การเกษตร' in program:
                continue
            
            status_id = row['status_id']
            count = row['count']
            
            if level not in data_summary:
                data_summary[level] = {"programs": {}}
            
            if program not in data_summary[level]["programs"]:
                data_summary[level]["programs"][program] = {"active": 0, "graduated": 0, "lost": 0, "success_rate": "0%"}
            
            grand_total += count
            if status_id in active_ids:
                data_summary[level]["programs"][program]["active"] += count
                total_active += count
            elif status_id in graduated_ids:
                data_summary[level]["programs"][program]["graduated"] += count
                total_graduated += count
            elif status_id in lost_ids:
                data_summary[level]["programs"][program]["lost"] += count
                total_lost += count

        
        for level in data_summary:
            for prog, stats in data_summary[level]["programs"].items():
                g = stats["graduated"]
                l = stats["lost"]
                if (g + l) > 0:
                    sr = round((g / (g + l)) * 100, 2)
                    stats["success_rate"] = f"{int(sr)}%" if sr == int(sr) else f"{sr}%"
                else:
                    stats["success_rate"] = "0%"

        overall_sr = "0%"
        if (total_graduated + total_lost) > 0:
            val = round((total_graduated / (total_graduated + total_lost)) * 100, 2)
            overall_sr = f"{int(val)}%" if val == int(val) else f"{val}%"

        result = {
            "analysis_overview": {
                "total_faculty": total_faculty,
                "total_research": total_research,
                "grand_total": grand_total,
                "total_active": total_active,
                "total_graduated": total_graduated,
                "total_lost": total_lost,
                "overall_success_rate": overall_sr
            },
            "data_summary": data_summary,
            "results": {}
        }
        
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"EXTERNAL-STATS error: {e}", exc_info=True)
        try:
            
            total_research = 0
            research_res = await db.execute(select(Faculty.scholar_data).where(Faculty.scholar_data != None))
            for s_data in research_res.scalars().all():
                if s_data:
                    try:
                        loaded = json.loads(s_data) if isinstance(s_data, str) else s_data
                        if isinstance(loaded, list):
                            total_research += len(loaded)
                    except Exception:
                        pass
        except:
            total_research = 0

        return {
            "status": "error",
            "message": "Internal error",
            "data": {
                "analysis_overview": {
                    "total_faculty": 0,
                    "total_research": total_research
                },
                "data_summary": {},
                "results": {}
            }
        }

def harden_scholar_data(data):
    """ทำความสะอาดข้อมูลเพื่อป้องกัน PII False Positive (เช่น Maestro CC BIN) และลดขนาด JSON"""
    if isinstance(data, list):
        return [harden_scholar_data(item) for item in data]
    elif isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            
            if k in ("cites_id", "serpapi_link"):
                continue
            
            if k == "link" or k == "thumbnail":
                if isinstance(v, str):
                    def mask_digits(match):
                        num = match.group(0)
                        if len(num) >= 12:
                            mid = len(num) // 2
                            return num[:mid-2] + "xxxx" + num[mid+2:]
                        return num
                    v = re.sub(r'\d{12,19}', mask_digits, v)
            elif isinstance(v, (str, int)):
                val_str = str(v)
                if val_str.isdigit() and len(val_str) >= 12:
                    mid = len(val_str) // 2
                    v = val_str[:mid-2] + "xxxx" + val_str[mid+2:]
            else:
                v = harden_scholar_data(v)
            cleaned[k] = v
        return cleaned
    return data

@router.get("/research")
async def api_research_list(db: AsyncSession = Depends(get_db)):
    """ดึงข้อมูลงานวิจัยทั้งหมด (SerpApi Organic Results) เรียงตามอาจารย์"""
    result = await db.execute(select(Faculty).where(Faculty.scholar_data != None).order_by(Faculty.id))
    faculty_rows = result.scalars().all()
    
    research_data = []
    for row in faculty_rows:
        img_val = row.image or ''
        img = img_val if img_val.startswith(("http", "/static", "data:", "/uploads")) else (f"https://ww2.agi.nu.ac.th/personnel/upload/{img_val}" if img_val else "")
        
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
            
        research_data.append(harden_scholar_data({
            'faculty_id': row.id,
            'name_th': f"{row.prefix or ''} {row.fname} {row.lname}".strip(),
            'name_en': f"{row.fname_en or ''} {row.lname_en or ''}".strip(),
            'image': img,
            'scholar_id': row.scholar_id,
            'publications': scholar_results,
            'metrics': metrics
        }))
        
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

        
        top_nre_rows = await db.execute(text("""
            SELECT c.company_name, COUNT(s.id) as cnt
            FROM public.coop_students s
            JOIN public.coop_companies c ON s.co_code = c.co_code
            WHERE s.major = 1
            GROUP BY c.company_name ORDER BY cnt DESC LIMIT 10
        """))
        top_nre = [{"name": r.company_name, "count": r.cnt} for r in top_nre_rows]

        
        top_geo_rows = await db.execute(text("""
            SELECT c.company_name, COUNT(s.id) as cnt
            FROM public.coop_students s
            JOIN public.coop_companies c ON s.co_code = c.co_code
            WHERE s.major = 2
            GROUP BY c.company_name ORDER BY cnt DESC LIMIT 10
        """))
        top_geo = [{"name": r.company_name, "count": r.cnt} for r in top_geo_rows]

        
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
        logger.error(f"COOP-STATS error: {e}", exc_info=True)
        return {"status": "error", "message": "Internal error"}

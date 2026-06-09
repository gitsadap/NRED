from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional
import math
import os
import pymssql
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class CurriculumStatsRequest(BaseModel):
    base_year: int

def get_student_db_connection():
    try:
        return pymssql.connect(
            server=os.getenv('STUDENT_DB_SERVER'),
            user=os.getenv('STUDENT_DB_USER'),
            password=os.getenv('STUDENT_DB_PASS'),
            database=os.getenv('STUDENT_DB_NAME')
        )
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def decode_thai(text):
    if not text or not isinstance(text, str):
        return text
        
    # If the text already has Thai characters, it's correct.
    if any('\u0e00' <= c <= '\u0e7f' for c in text):
        return text
        
    try:
        # Try to encode to cp1252 (Windows default encoding for non-unicode bytes)
        try:
            raw_bytes = text.encode('cp1252')
        except UnicodeEncodeError:
            # Fallback to latin1 with replace to avoid crashes
            raw_bytes = text.encode('latin1', errors='replace')
            
        # Decode back to Thai using cp874 (TIS-620)
        return raw_bytes.decode('cp874', errors='replace')
    except Exception:
        return text

@router.get("/curriculum-stats")
def get_curriculum_stats(base_year: int = Query(2569, description="ปีเริ่มต้นการค้นหา เช่น 2569")):
    conn = get_student_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
        
    cursor = conn.cursor(as_dict=True)
    start_year = base_year - 4
    end_year = base_year
    
    try:
        # Status groups
        active_ids = {10, 11, 12}
        graduated_ids = {40}
        lost_ids = {21, 22, 50, 51, 52, 60}
        
        # We need older data to calculate graduation rate.
        # e.g., Graduation in base_year requires cohort from base_year - 3 or 4.
        db_start_year = base_year - 8
        
        query = """
            SELECT 
                PROGRAMNAME, LEVGROUPNAME, STDADMITYEAR, STDSTATUSID, STDFINISHDATE
            FROM [Agri].[View_Student4AgriFaculty]
            WHERE STDADMITYEAR BETWEEN %d AND %d
              AND (
                  PROGRAMNAME LIKE N'%%สิ่งแวดล้อม%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิศาสตร์%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิสารสนเทศ%%' OR
                  PROGRAMNAME LIKE N'%%อวกาศ%%' OR
                  PROGRAMNAME LIKE N'%%ทรัพยากรธรรมชาติ%%'
              )
              AND PROGRAMNAME NOT LIKE N'%%วิทยาศาสตร์การเกษตร%%'
        """ % (db_start_year, end_year)
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        programs_data = {}
        for r in rows:
            prog = decode_thai(r.get('programname') or r.get('PROGRAMNAME'))
            lev = decode_thai(r.get('levgroupname') or r.get('LEVGROUPNAME'))
            
            if not prog: continue
                
            key = (lev, prog)
            if key not in programs_data:
                # Initialize cohorts from db_start_year to end_year
                programs_data[key] = {
                    "cohorts": { y: {"admitted": 0, "active": 0, "graduated": 0, "lost_cohort": 0} for y in range(db_start_year, end_year + 1) },
                    "graduates_by_year": { y: 0 for y in range(start_year, end_year + 1) },
                    "lost_by_year": { y: {"total": 0, "y1": 0, "y2": 0, "y3": 0, "y4": 0, "other": 0} for y in range(start_year, end_year + 1) }
                }
                
            p_data = programs_data[key]
            
            st = r.get('stdstatusid') or r.get('STDSTATUSID')
            admit_year = r.get('stdadmityear') or r.get('STDADMITYEAR')
            finish_date = r.get('stdfinishdate') or r.get('STDFINISHDATE')
            if start_year <= admit_year <= end_year:
                if admit_year not in p_data["cohorts"]:
                    p_data["cohorts"][admit_year] = {"admitted": 0, "active": 0, "graduated": 0}
                
                cohort = p_data["cohorts"][admit_year]
                cohort["admitted"] += 1
                
                if st in active_ids:
                    cohort["active"] += 1
            
            # Handle graduates by finish year
            if st in graduated_ids and finish_date:
                try:
                    if hasattr(finish_date, 'year'):
                        cal_year = finish_date.year
                        cal_month = finish_date.month
                    else:
                        cal_year = int(str(finish_date)[:4])
                        cal_month = int(str(finish_date)[5:7])
                        
                    if cal_month < 7:
                        fy = cal_year + 543 - 1
                    else:
                        fy = cal_year + 543
                        
                    if start_year <= fy <= end_year:
                        p_data["graduates_by_year"][fy] += 1
                except Exception:
                    pass
            
            # Handle lost (dropouts) by dropout academic year
            elif st in lost_ids:
                # Need to determine dropout academic year
                dy = None
                if finish_date:
                    try:
                        if hasattr(finish_date, 'year'):
                            cal_year = finish_date.year
                            cal_month = finish_date.month
                        else:
                            cal_year = int(str(finish_date)[:4])
                            cal_month = int(str(finish_date)[5:7])
                        
                        dy = cal_year + 543 - 1 if cal_month < 7 else cal_year + 543
                    except Exception:
                        pass
                
                # If dy is valid and within range
                if dy and start_year <= dy <= end_year:
                    yl = dy - admit_year + 1
                    lost_record = p_data["lost_by_year"][dy]
                    lost_record["total"] += 1
                    if yl == 1:
                        lost_record["y1"] += 1
                    elif yl == 2:
                        lost_record["y2"] += 1
                    elif yl == 3:
                        lost_record["y3"] += 1
                    elif yl >= 4:
                        lost_record["y4"] += 1
                    else:
                        lost_record["other"] += 1
                # To still support cohort-based attrition rate
                if start_year <= admit_year <= end_year:
                    if "lost_cohort" not in p_data["cohorts"][admit_year]:
                        p_data["cohorts"][admit_year]["lost_cohort"] = 0
                    p_data["cohorts"][admit_year]["lost_cohort"] += 1

        result = []
        for (lev, prog), data in programs_data.items():
            cohorts = data["cohorts"]
            grad_years = data["graduates_by_year"]
            
            # Format output correctly
            out = {
                "level": lev,
                "program": prog,
                "admitted": {},
                "active": {},
                "lost": {},
                "attrition_rate": {},
                "graduated": {},
                "grad_rate": {},
                "retention_rate": {}
            }
            
            # Calculate metrics for the last 5 years
            for y in range(start_year, end_year + 1):
                c = cohorts[y]
                total = c["admitted"]
                
                out["admitted"][str(y)] = total
                out["active"][str(y)] = c["active"]
                
                # Lost data is grouped by dropout academic year
                out["lost"][str(y)] = data["lost_by_year"][y]
                
                # Attrition rate uses the cohort's own dropouts
                lost_total_cohort = c.get("lost_cohort", 0)
                out["attrition_rate"][str(y)] = round((lost_total_cohort / total * 100), 2) if total > 0 else 0
                out["retention_rate"][str(y)] = round(((c["active"] + c["graduated"]) / total * 100), 2) if total > 0 else 0
                
                # Graduation is based on Finish Year, dividing by Cohort y-3
                grad_count = grad_years[y]
                out["graduated"][str(y)] = grad_count
                
                cohort_for_grad = cohorts.get(y - 3, {})
                # Deduct lost students (ลาออก/ย้ายสาขา) from the denominator as requested
                lost_for_grad = cohort_for_grad.get("lost_cohort", 0)
                grad_denominator = cohort_for_grad.get("admitted", 0) - lost_for_grad
                out["grad_rate"][str(y)] = round((grad_count / grad_denominator * 100), 2) if grad_denominator > 0 else 0

            result.append(out)
            
        result.sort(key=lambda x: (x['level'], x['program']))
            
        return {
            "base_year": base_year,
            "start_year": start_year,
            "end_year": end_year,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

PROVINCE_MAPPING = {
    10: 'กรุงเทพมหานคร', 11: 'สมุทรปราการ', 12: 'นนทบุรี', 13: 'ปทุมธานี', 14: 'พระนครศรีอยุธยา', 15: 'อ่างทอง', 16: 'ลพบุรี', 17: 'สิงห์บุรี', 18: 'ชัยนาท', 19: 'สระบุรี',
    20: 'ชลบุรี', 21: 'ระยอง', 22: 'จันทบุรี', 23: 'ตราด', 24: 'ฉะเชิงเทรา', 25: 'ปราจีนบุรี', 26: 'นครนายก', 27: 'สระแก้ว',
    30: 'นครราชสีมา', 31: 'บุรีรัมย์', 32: 'สุรินทร์', 33: 'ศรีสะเกษ', 34: 'อุบลราชธานี', 35: 'ยโสธร', 36: 'ชัยภูมิ', 37: 'อำนาจเจริญ', 38: 'บึงกาฬ', 39: 'หนองบัวลำภู',
    40: 'ขอนแก่น', 41: 'อุดรธานี', 42: 'เลย', 43: 'หนองคาย', 44: 'มหาสารคาม', 45: 'ร้อยเอ็ด', 46: 'กาฬสินธุ์', 47: 'สกลนคร', 48: 'นครพนม', 49: 'มุกดาหาร',
    50: 'เชียงใหม่', 51: 'ลำพูน', 52: 'ลำปาง', 53: 'อุตรดิตถ์', 54: 'แพร่', 55: 'น่าน', 56: 'พะเยา', 57: 'เชียงราย', 58: 'แม่ฮ่องสอน',
    60: 'นครสวรรค์', 61: 'อุทัยธานี', 62: 'กำแพงเพชร', 63: 'ตาก', 64: 'สุโขทัย', 65: 'พิษณุโลก', 66: 'พิจิตร', 67: 'เพชรบูรณ์',
    70: 'ราชบุรี', 71: 'กาญจนบุรี', 72: 'สุพรรณบุรี', 73: 'นครปฐม', 74: 'สมุทรสาคร', 75: 'สมุทรสงคราม', 76: 'เพชรบุรี', 77: 'ประจวบคีรีขันธ์',
    80: 'นครศรีธรรมราช', 81: 'กระบี่', 82: 'พังงา', 83: 'ภูเก็ต', 84: 'สุราษฎร์ธานี', 85: 'ระนอง', 86: 'ชุมพร',
    90: 'สงขลา', 91: 'สตูล', 92: 'ตรัง', 93: 'พัทลุง', 94: 'ปัตตานี', 95: 'ยะลา', 96: 'นราธิวาส'
}

@router.get("/province-stats")
def get_province_stats(base_year: int = Query(2569)):
    conn = get_student_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT HOMEPROVINCEID, CONTACTPROVINCEID, LEVGROUPNAME, PROGRAMNAME
            FROM [Agri].[View_Student4AgriFaculty]
            WHERE STDADMITYEAR = %s
              AND (
                  PROGRAMNAME LIKE N'%%สิ่งแวดล้อม%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิศาสตร์%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิสารสนเทศ%%' OR
                  PROGRAMNAME LIKE N'%%อวกาศ%%' OR
                  PROGRAMNAME LIKE N'%%ทรัพยากรธรรมชาติ%%'
              )
              AND PROGRAMNAME NOT LIKE N'%%วิทยาศาสตร์การเกษตร%%'
        """, (base_year,))
        
        rows = cursor.fetchall()
        
        counts = {}
        for r in rows:
            prog = decode_thai(r.get('PROGRAMNAME') or r.get('programname'))
            lev = decode_thai(r.get('LEVGROUPNAME') or r.get('levgroupname'))
            
            if not prog: continue
                
            prov_id = r.get('HOMEPROVINCEID')
            if not prov_id or str(prov_id).strip() == '0' or str(prov_id).strip() == 'None':
                prov_id = r.get('CONTACTPROVINCEID')
                
            try:
                pid = int(prov_id)
            except (ValueError, TypeError):
                pid = 0
            
            counts[pid] = counts.get(pid, 0) + 1
        
        results = []
        total_valid_students = 0
        for pid, count in counts.items():
            total_valid_students += count
            if pid == 0:
                thai_name = "ไม่ระบุ"
                iso_code = "UNKNOWN"
            else:
                thai_name = PROVINCE_MAPPING.get(pid, "ไม่ระบุ")
                iso_code = f"TH-{pid:02d}"
            
            results.append({
                "raw_pid": pid,
                "id": iso_code,
                "province_name": thai_name,
                "count": count
            })
            
        results.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "base_year": base_year,
            "total_students": total_valid_students,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/province-students")
def get_province_students(base_year: int = Query(..., description="ปีการศึกษาอ้างอิง"), province_id: int = Query(..., description="ID จังหวัด (0 = ไม่ระบุ)")):
    conn = get_student_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
        
    try:
        cursor = conn.cursor(as_dict=True)
        
        # Build query
        query = """
            SELECT STDCODE, PREFIXNAME, STDNAME, STDSURNAME, PROGRAMNAME, LEVGROUPNAME, HOMEPROVINCEID, CONTACTPROVINCEID
            FROM [Agri].[View_Student4AgriFaculty]
            WHERE STDADMITYEAR = %s
              AND (
                  PROGRAMNAME LIKE N'%%สิ่งแวดล้อม%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิศาสตร์%%' OR
                  PROGRAMNAME LIKE N'%%ภูมิสารสนเทศ%%' OR
                  PROGRAMNAME LIKE N'%%อวกาศ%%' OR
                  PROGRAMNAME LIKE N'%%ทรัพยากรธรรมชาติ%%'
              )
              AND PROGRAMNAME NOT LIKE N'%%วิทยาศาสตร์การเกษตร%%'
        """
        
        cursor.execute(query, (base_year,))
        rows = cursor.fetchall()
        
        students = []
        for r in rows:
            prog = decode_thai(r.get('PROGRAMNAME') or r.get('programname'))
            lev = decode_thai(r.get('LEVGROUPNAME') or r.get('levgroupname'))
            prefix = decode_thai(r.get('PREFIXNAME') or r.get('prefixname') or '')
            fname = decode_thai(r.get('STDNAME') or r.get('stdname') or '')
            lname = decode_thai(r.get('STDSURNAME') or r.get('stdsurname') or '')
            
            if not prog: continue
                
            prov_id = r.get('HOMEPROVINCEID')
            if not prov_id or str(prov_id).strip() == '0' or str(prov_id).strip() == 'None':
                prov_id = r.get('CONTACTPROVINCEID')
                
            try:
                pid = int(prov_id)
            except (ValueError, TypeError):
                pid = 0
                
            if pid == province_id:
                std_code = str(r.get('STDCODE') or r.get('stdcode') or '')
                full_name = f"{prefix}{fname} {lname}".strip()
                
                students.append({
                    "id": std_code,
                    "name": full_name,
                    "program": prog,
                    "level": lev
                })
                
        # Sort by program then stdcode
        students.sort(key=lambda x: (x["program"], x["id"]))
        
        return {
            "base_year": base_year,
            "province_id": province_id,
            "total": len(students),
            "students": students
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

import pymssql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymssql.connect(
    server=os.getenv('STUDENT_DB_SERVER'),
    user=os.getenv('STUDENT_DB_USER'),
    password=os.getenv('STUDENT_DB_PASS'),
    database=os.getenv('STUDENT_DB_NAME')
)
cursor = conn.cursor(as_dict=True)

# These are the programs from old_api.json
old_programs = {
    'การจัดการทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แผน ก แบบ ก 1)',
    'การจัดการทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แผน ก แบบ ก 2)',
    'การจัดการทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แผน ข)',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 1.1)',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 1.1) - นานาชาติ',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 2.1)',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 2.1) - นานาชาติ',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 2.2)',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แบบ 2.2) - นานาชาติ',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แผน ก แบบ ก 1)',
    'ทรัพยากรธรรมชาติและสิ่งแวดล้อม - (แผน ก แบบ ก 2)',
    'ภูมิศาสตร์',
    'ภูมิสารสนเทศศาสตร์',
    'ภูมิสารสนเทศศาสตร์ - (แผน ก แบบ ก 1)',
    'ภูมิสารสนเทศศาสตร์ - (แผน ก แบบ ก 2)',
    'วิทยาศาสตร์สิ่งแวดล้อม - (แบบ 1.1)',
    'วิทยาศาสตร์สิ่งแวดล้อม - (แบบ 2.1)',
    'วิทยาศาสตร์สิ่งแวดล้อม - (แผน ก แบบ ก 1)',
    'วิทยาศาสตร์สิ่งแวดล้อม - (แผน ก แบบ ก 2)',
    'เทคโนโลยีอวกาศและภูมิสารสนเทศ - (แบบ 1.1)',
    'เทคโนโลยีอวกาศและภูมิสารสนเทศ - (แผน ก แบบ ก 2)'
}

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

grand_total = 0
total_active = 0
total_graduated = 0
total_lost = 0

active_ids = {10, 11, 12}
graduated_ids = {40}
lost_ids = {21, 22, 50, 51, 52, 60}

for r in rows:
    prog = r['program']
    # if prog not in old_programs:
    if not any(k in prog for k in ['สิ่งแวดล้อม', 'ภูมิศาสตร์', 'ภูมิสารสนเทศ', 'อวกาศ', 'ทรัพยากรธรรมชาติ']):
        continue
    if 'วิทยาศาสตร์การเกษตร' in prog:
        continue
        
    count = r['count']
    st = r['status_id']
    
    grand_total += count
    if st in active_ids:
        total_active += count
    elif st in graduated_ids:
        total_graduated += count
    elif st in lost_ids:
        total_lost += count

print(f"Grand Total: {grand_total}")
print(f"Graduated: {total_graduated}")
print(f"Active: {total_active}")
print(f"Lost: {total_lost}")

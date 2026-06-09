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

sql = """
SELECT DISTINCT STDFACULTYID, FACULTYNAME, STDDEPARTMENTID, DEPARTMENTNAME, PROGRAMNAME
FROM [Agri].[View_Student4AgriFaculty]
WHERE PROGRAMNAME LIKE '%สิ่งแวดล้อม%' OR PROGRAMNAME LIKE '%ภูมิสารสนเทศ%' OR PROGRAMNAME LIKE '%ภูมิศาสตร์%'
"""
cursor.execute(sql)
rows = cursor.fetchall()
for r in rows:
    print(f"FAC: {r['STDFACULTYID']} ({r['FACULTYNAME']}), DEP: {r['STDDEPARTMENTID']} ({r['DEPARTMENTNAME']}) -> {r['PROGRAMNAME']}")

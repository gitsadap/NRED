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
cursor.execute("SELECT PROGRAMID, PROGRAMNAME, COUNT(*) as c FROM [Agri].[View_Student4AgriFaculty] WHERE STDADMITYEAR = 2569 GROUP BY PROGRAMID, PROGRAMNAME")
rows = cursor.fetchall()
for r in rows:
    if 'วิทยาศาสตร์การเกษตร' not in r['PROGRAMNAME']:
        print(r['PROGRAMNAME'], r['c'])

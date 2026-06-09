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
cursor.execute("SELECT STDADMITYEAR, COUNT(*) as c FROM [Agri].[View_Student4AgriFaculty] WHERE STDSTATUSID IN (21, 22, 50, 51, 52, 60) AND STDFINISHDATE IS NULL AND STDADMITYEAR >= 2560 GROUP BY STDADMITYEAR ORDER BY STDADMITYEAR")
rows = cursor.fetchall()
for r in rows:
    print(r)

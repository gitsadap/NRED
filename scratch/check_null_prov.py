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
cursor.execute("""
SELECT STDADMITYEAR, 
       COUNT(*) as Total, 
       SUM(CASE WHEN HOMEPROVINCEID IS NULL THEN 1 ELSE 0 END) as Nulls
FROM [Agri].[View_Student4AgriFaculty]
GROUP BY STDADMITYEAR
ORDER BY STDADMITYEAR DESC
""")
rows = cursor.fetchall()
for r in rows:
    print(r)

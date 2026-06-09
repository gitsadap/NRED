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
cursor.execute("SELECT TOP 1 * FROM [Agri].[View_Student4AgriFaculty] WHERE STDADMITYEAR = 2569")
rows = cursor.fetchall()
for k, v in rows[0].items():
    if 'PROV' in k.upper():
        print(f"{k}: {v}")

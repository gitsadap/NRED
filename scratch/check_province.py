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
cursor.execute("SELECT TOP 5 * FROM [Agri].[View_Student4AgriFaculty]")
rows = cursor.fetchall()
if rows:
    for k, v in rows[0].items():
        print(f"{k}: {v}")

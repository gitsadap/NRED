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

# 1. Get min, max STDADMITYEAR
cursor.execute('SELECT MIN(STDADMITYEAR) as min_y, MAX(STDADMITYEAR) as max_y FROM [Agri].[View_Student4AgriFaculty]')
year_range = cursor.fetchone()
print(f"Admit year range: {year_range}")

# 2. Let's check how many rows have STDFINISHDATE and what it looks like
cursor.execute('SELECT TOP 5 STDFINISHDATE FROM [Agri].[View_Student4AgriFaculty] WHERE STDFINISHDATE IS NOT NULL')
print("Sample STDFINISHDATE:", cursor.fetchall())

# 3. Are there columns for current year or graduation year?
# Checking if there's any other useful column
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='View_Student4AgriFaculty'")
columns = [r['COLUMN_NAME'] for r in cursor.fetchall()]
print("All columns:", columns)


import pymssql
import os
import time
from dotenv import load_dotenv

load_dotenv()
print("Connecting...")
start = time.time()
try:
    conn = pymssql.connect(
        server=os.getenv('STUDENT_DB_SERVER'),
        user=os.getenv('STUDENT_DB_USER'),
        password=os.getenv('STUDENT_DB_PASS'),
        database=os.getenv('STUDENT_DB_NAME')
    )
    print(f"Connected in {time.time() - start:.2f} seconds!")
    cursor = conn.cursor(as_dict=True)
    cursor.execute("SELECT TOP 1 * FROM [Agri].[View_Student4AgriFaculty]")
    print(cursor.fetchall())
except Exception as e:
    print(f"Failed to connect: {e}")

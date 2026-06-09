import os
from dotenv import load_dotenv
import pymssql
load_dotenv()
conn = pymssql.connect(
    server=os.getenv('STUDENT_DB_SERVER'),
    user=os.getenv('STUDENT_DB_USER'),
    password=os.getenv('STUDENT_DB_PASS'),
    database=os.getenv('STUDENT_DB_NAME')
)
cursor = conn.cursor(as_dict=True)
query = """
    SELECT TOP 1 STDCODE, PREFIXNAME, STDNAME, STDSURNAME, PROGRAMNAME, LEVGROUPNAME, HOMEPROVINCEID, CONTACTPROVINCEID
    FROM [Agri].[View_Student4AgriFaculty]
"""
cursor.execute(query)
print(cursor.fetchone())

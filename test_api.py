import requests

try:
    r = requests.get('http://127.0.0.1:8000/api/dashboard/province-students?base_year=2566&province_id=65')
    print(r.json())
except Exception as e:
    print("Error:", e)

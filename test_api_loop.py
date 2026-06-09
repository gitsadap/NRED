import requests
import time

for _ in range(10):
    try:
        r = requests.get('http://127.0.0.1:8000/api/dashboard/province-students?base_year=2566&province_id=65')
        data = r.json()
        if 'students' in data:
            print(data['students'][:2])
            break
        print("Response:", data)
    except Exception as e:
        print("Error:", e)
    time.sleep(2)

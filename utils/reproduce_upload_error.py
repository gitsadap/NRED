import requests

url = "http://localhost:8099/api/faculty/upload-cv"
files = {'file': ('test_cv.pdf', b'%PDF-1.4 dummy content')}
data = {'user_id': '1'}

try:
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
except Exception as e:
    print(f"Error: {e}")

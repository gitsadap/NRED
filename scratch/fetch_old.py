import urllib.request
import json

url = "https://oassar.agi.nu.ac.th/esprel/vendor/include/info.php"
try:
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode('utf-8'))
    with open('scratch/old_api.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Success")
except Exception as e:
    print(f"Error: {e}")

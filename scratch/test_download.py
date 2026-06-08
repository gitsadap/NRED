import urllib.request
import os

url = "https://ww2.agi.nu.ac.th/nred/cv/cv_Gitsada.pdf"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

req = urllib.request.Request(url, headers=headers)
try:
    print(f"Downloading {url}...")
    with urllib.request.urlopen(req) as response:
        content = response.read()
        print(f"Success! Downloaded {len(content)} bytes.")
        
        # Save locally to test
        os.makedirs("public/uploads", exist_ok=True)
        test_path = "public/uploads/test_cv_gitsada.pdf"
        with open(test_path, "wb") as f:
            f.write(content)
        print(f"Saved to {test_path}, size: {os.path.getsize(test_path)} bytes")
except Exception as e:
    print("Download failed:", e)

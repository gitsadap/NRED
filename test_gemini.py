import os, sys
os.chdir('F:/apps/nred')
sys.path.insert(0, 'F:/apps/nred')
from dotenv import load_dotenv
load_dotenv()
from app.config import settings
import litellm

print("Gemini key:", settings.gemini_api_key[:12] + "..." if settings.gemini_api_key else "NONE")

try:
    r = litellm.completion(
        model="gemini/gemini-2.0-flash",
        messages=[{"role": "user", "content": "translate ทดสอบ to English, reply with just the word"}],
        api_key=settings.gemini_api_key,
        max_tokens=50
    )
    print("OK:", r.choices[0].message.content)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:500])

import asyncio
import litellm
import os

from app.config import settings

async def main():
    gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    try:
        res = await litellm.aembedding(
            model="gemini/text-embedding-004", 
            input=["test"],
            api_key=gemini_key
        )
        print("Success 1:", res.data[0]["embedding"][:3])
    except Exception as e:
        print("Error 1:", e)
        
    try:
        res = await litellm.aembedding(
            model="text-embedding-004", 
            input=["test"],
            api_key=gemini_key
        )
        print("Success 2:", res.data[0]["embedding"][:3])
    except Exception as e:
        print("Error 2:", e)

asyncio.run(main())

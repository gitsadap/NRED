import asyncio
import litellm
import os

from litellm import acompletion

async def main():
    from app.config import settings
    gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    # Create consecutive user messages
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "user", "content": "Hello again"}
    ]
    try:
        response = await litellm.acompletion(
            model="gemini/gemini-3.1-flash-lite-preview",
            messages=messages,
            api_key=gemini_key,
            temperature=0.3,
            max_tokens=800
        )
        print("Success!")
    except Exception as e:
        print(f"Failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(main())

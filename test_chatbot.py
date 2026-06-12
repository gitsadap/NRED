import asyncio
from app.routers.chatbot import get_chatbot_response, ChatRequest

async def main():
    req = ChatRequest(
        message="สวัสดีครับ",
        history=[],
        level="ปริญญาตรี",
        program="ทรัพยากรธรรมชาติและสิ่งแวดล้อม (NRE)"
    )
    res = await get_chatbot_response(req)
    print("Response:", res)

if __name__ == "__main__":
    asyncio.run(main())

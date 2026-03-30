import nest_asyncio
nest_asyncio.apply()
from playwright.sync_api import sync_playwright
import time

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser PageError: {err}"))
        print("Navigating to page...")
        page.goto("http://127.0.0.1:8099/research", wait_until="networkidle")
        time.sleep(2)
        print("Page Title:", page.title())
        browser.close()
except Exception as e:
    print(f"Playwright error: {e}")

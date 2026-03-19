"""
Debug KDP session - check if cookies are being applied correctly.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.vault.store import SessionVault
from playwright.async_api import async_playwright


async def main():
    vault = SessionVault()
    session_data = vault.load("kdp")
    storage_state = session_data.get("storage_state", {})
    cookies = session_data.get("cookies", [])
    
    print(f"Storage state cookies: {len(storage_state.get('cookies', []))}")
    print(f"Raw cookies in session: {len(cookies)}")
    
    # Check amazon.com cookies
    for c in storage_state.get('cookies', []):
        if 'session' in c.get('name', '').lower() or 'token' in c.get('name', '').lower() or 'at-main' in c.get('name', '').lower():
            import time
            exp = c.get('expires', -1)
            is_expired = exp != -1 and exp < time.time()
            print(f"  Cookie: {c.get('name')} domain={c.get('domain')} "
                  f"expires={exp} {'EXPIRED' if is_expired else 'valid'}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )
        
        # Try with storage state
        context = await browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        
        # Try bookshelf first
        print("\nNavigating to KDP bookshelf...")
        await page.goto("https://kdp.amazon.com/en_US/bookshelf", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")
        
        is_logged_in = "bookshelf" in page.url and "signin" not in page.url
        print(f"Logged in: {is_logged_in}")
        
        if not is_logged_in:
            # Check cookies applied
            applied_cookies = await context.cookies()
            print(f"\nApplied cookies in browser: {len(applied_cookies)}")
            for c in applied_cookies[:10]:
                print(f"  {c.get('name')}: domain={c.get('domain')}")
            
            # Try manually adding cookies
            print("\nTrying to add cookies manually...")
            await context.add_cookies(cookies)
            await page.goto("https://kdp.amazon.com/en_US/bookshelf", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            print(f"URL after adding cookies: {page.url}")
            print(f"Logged in: {'bookshelf' in page.url}")
        
        await page.screenshot(path="/tmp/kdp_session_debug.png")
        await browser.close()


asyncio.run(main())

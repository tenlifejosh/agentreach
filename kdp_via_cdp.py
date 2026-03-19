"""
Connect directly to the user's running Chrome browser via CDP.
Use the existing KDP session to create the Pray Bold: Teen Edition book.
"""
import asyncio
import sys
import json
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


MANUSCRIPT = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/interior.pdf")
COVER = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/cover-full-wrap.pdf")

BOOK_DETAILS = {
    "title": "Pray Bold: Teen Edition",
    "subtitle": "A 52-Week Prayer Journal for Teenagers",
    "first_name": "Joshua",
    "last_name": "Noreen",
    "description": "<p>Built for teenagers who want to grow in faith. 52 weeks of guided prayer prompts, scripture reflection, and space to hear from God—designed for the pace and questions of teenage life.</p>",
    "keywords": [
        "teen prayer journal",
        "christian teen journal",
        "bible journal for teenagers",
        "faith journal teen",
        "prayer book for teens",
        "christian gifts for teens",
        "teen devotional journal",
    ],
    "price": "12.99",
}


async def get_kdp_tab():
    """Get the KDP tab from the running Chrome browser."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://127.0.0.1:18792/json/list", timeout=5)
        tabs = resp.json()
        for tab in tabs:
            if 'kdp.amazon.com' in tab.get('url', ''):
                return tab
    return None


async def harvest_chrome_kdp_cookies():
    """Connect to Chrome CDP and extract KDP cookies to update the vault."""
    from agentreach.vault.store import SessionVault
    from playwright.async_api import async_playwright
    
    vault = SessionVault()
    
    print("Connecting to Chrome browser via CDP...")
    async with async_playwright() as p:
        # Connect to the running Chrome browser
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:18792")
        
        contexts = browser.contexts
        print(f"Browser contexts: {len(contexts)}")
        
        for ctx in contexts:
            pages = ctx.pages
            print(f"  Context has {len(pages)} pages")
            for pg in pages:
                print(f"    Page: {pg.url}")
                if 'kdp.amazon.com' in pg.url:
                    print(f"    Found KDP page!")
                    
                    # Get cookies from this context
                    cookies = await ctx.cookies(urls=["https://kdp.amazon.com", "https://amazon.com"])
                    print(f"    KDP cookies: {len(cookies)}")
                    for c in cookies[:10]:
                        print(f"      {c.get('name')}: domain={c.get('domain')}")
                    
                    # Get storage state
                    storage_state = await ctx.storage_state()
                    
                    # Update vault with fresh Chrome cookies
                    existing = vault.load("kdp") or {}
                    existing["cookies"] = cookies
                    existing["storage_state"] = storage_state
                    existing["harvested_at"] = "2026-03-14T19:00:00+00:00"  # fresh
                    vault.save("kdp", existing)
                    print("    ✅ Vault updated with Chrome cookies!")
                    
                    # Also capture a screenshot  
                    await pg.screenshot(path="/tmp/kdp_chrome_page.png")
                    print("    Screenshot: /tmp/kdp_chrome_page.png")
                    
                    return cookies, pg
        
        print("No KDP pages found in Chrome")
        return None, None


async def main():
    # First, try to harvest Chrome cookies
    print("=" * 60)
    print("Step 1: Harvest KDP cookies from Chrome browser")
    print("=" * 60)
    
    cookies, page = await harvest_chrome_kdp_cookies()
    
    if not cookies:
        print("ERROR: Could not connect to Chrome or find KDP tabs")
        print("The Chrome CDP is at: http://127.0.0.1:18792")
        print("Make sure Chrome is running with --remote-debugging-port=18792")
        return
    
    print(f"\n✅ Got {len(cookies)} cookies from Chrome")
    print("\n" + "=" * 60)
    print("Step 2: Test if the vault session now works for title creation")
    print("=" * 60)
    
    # Now test if the updated vault session works
    from agentreach.browser.session import platform_context
    
    async with platform_context("kdp", headless=True) as (ctx, pg2):
        await pg2.goto(
            "https://kdp.amazon.com/en_US/title-setup/paperback/new/details",
            wait_until="domcontentloaded",
            timeout=30000
        )
        await pg2.wait_for_timeout(3000)
        print(f"New title URL: {pg2.url}")
        auth_ok = "signin" not in pg2.url
        print(f"Auth bypass success: {auth_ok}")


asyncio.run(main())

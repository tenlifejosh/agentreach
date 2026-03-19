"""Check products dashboard and fix publish state of FamliClaw."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault

PRODUCT_ID = "fhlmxiz"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
DASHBOARD_URL = "https://gumroad.com/products"

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        # First check dashboard
        print("=== Checking products dashboard ===")
        await page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(screenshots_dir / "dash_01.png"), full_page=True)
        
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print("Dashboard content:")
        for line in lines[:60]:
            print(f"  {line}")
        
        # Look for FamliClaw in the list
        famliclaw_visible = "FamliClaw" in body or "FamiliClaw" in body
        print(f"\nFamliClaw/FamiliClaw on dashboard: {famliclaw_visible}")
        
        # Now navigate to edit page
        print("\n=== Navigating to edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(screenshots_dir / "edit_02.png"), full_page=True)
        
        body2 = await page.locator("body").inner_text()
        lines2 = [l.strip() for l in body2.split('\n') if l.strip()]
        print("Edit page first 30 lines:")
        for line in lines2[:30]:
            print(f"  {line}")

        # List all buttons
        buttons = page.locator("button")
        btn_count = await buttons.count()
        print(f"\nAll buttons ({btn_count}):")
        for i in range(min(btn_count, 25)):
            try:
                text = await buttons.nth(i).inner_text()
                visible = await buttons.nth(i).is_visible()
                if text.strip():
                    print(f"  [{i}] visible={visible} '{text.strip()}'")
            except:
                pass

        # Try to find and click Publish
        # It might be a link or different button
        all_btns = page.locator("button, [role='button']")
        all_count = await all_btns.count()
        print(f"\nAll clickable elements: {all_count}")
        for i in range(min(all_count, 30)):
            try:
                text = await all_btns.nth(i).inner_text()
                if "publish" in text.lower() or "live" in text.lower() or "save" in text.lower():
                    visible = await all_btns.nth(i).is_visible()
                    print(f"  FOUND [{i}] visible={visible} '{text.strip()}'")
            except:
                pass

asyncio.run(main())

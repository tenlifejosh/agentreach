"""Re-publish FamliClaw — it was accidentally unpublished."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault

PRODUCT_ID = "fhlmxiz"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        body = await page.locator("body").inner_text()
        
        # Check state
        publish_btn = page.locator('button:has-text("Publish")').first
        unpublish_btn = page.locator('button:has-text("Unpublish")').first
        
        publish_count = await publish_btn.count()
        unpublish_count = await unpublish_btn.count()
        
        print(f"Publish button count: {publish_count}")
        print(f"Unpublish button count: {unpublish_count}")
        
        if publish_count > 0 and unpublish_count == 0:
            btn_text = await publish_btn.inner_text()
            print(f"Found publish button: '{btn_text}' — clicking to publish!")
            await publish_btn.click()
            await page.wait_for_timeout(4000)
            await page.screenshot(path=str(screenshots_dir / "republish_01.png"), full_page=True)
            
            # Verify
            body2 = await page.locator("body").inner_text()
            unpub_after = await page.locator('button:has-text("Unpublish")').count()
            print(f"After publish, Unpublish button present: {unpub_after > 0}")
            if unpub_after > 0:
                print("✅ Product is now LIVE/Published!")
        elif unpublish_count > 0:
            print("✅ Product is already published (Unpublish button visible) — no action needed.")
        else:
            print("⚠️  Unclear state. Page content:")
            lines = [l.strip() for l in body.split('\n') if l.strip()]
            for line in lines[:30]:
                print(f"  {line}")

asyncio.run(main())

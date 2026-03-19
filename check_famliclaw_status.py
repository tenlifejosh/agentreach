"""Check FamliClaw publication status and custom URL."""
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
        await page.screenshot(path=str(screenshots_dir / "status_01.png"), full_page=True)

        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print("Page content:")
        for line in lines[:80]:
            print(f"  {line}")

        # Check published state
        pub_count = await page.locator('text="Published"').count()
        unpub_count = await page.locator('text="Unpublished"').count()
        print(f"\nPublished indicators: {pub_count}")
        print(f"Unpublished indicators: {unpub_count}")

        # Check custom URL field (placeholder 'fhlmxiz')
        custom_url_input = page.locator('input[placeholder="fhlmxiz"]').first
        if await custom_url_input.count() > 0:
            custom_url = await custom_url_input.input_value()
            print(f"Custom URL value: '{custom_url}'")
        
        # Check name
        name_input = page.locator('input[id$="-name"]').first
        if await name_input.count() > 0:
            name = await name_input.input_value()
            print(f"Product name: '{name}'")

        # Look for toggle button for published state
        toggles = page.locator('button[role="switch"], input[type="checkbox"]')
        t_count = await toggles.count()
        print(f"\nToggle/checkbox count: {t_count}")

        # Check if there's a publish button
        publish_btn = page.locator('button:has-text("Publish")').first
        if await publish_btn.count() > 0:
            btn_text = await publish_btn.inner_text()
            print(f"Publish button: '{btn_text}'")
            await publish_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(screenshots_dir / "status_02_published.png"), full_page=True)
            print("Clicked publish!")

asyncio.run(main())

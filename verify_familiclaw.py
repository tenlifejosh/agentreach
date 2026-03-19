"""
Verify FamiliClaw is published and check its state.
Also ensure description is set and publish it if not yet published.
"""
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
        print("=== Navigating to product edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(screenshots_dir / "fc_01_edit.png"), full_page=True)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Check page content
        body_text = await page.locator("body").inner_text()
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        print("\nPage content (first 60 lines):")
        for line in lines[:60]:
            print(f"  {line}")

        # Check if published
        published_count = await page.locator('text="Published"').count()
        unpublished_count = await page.locator('text="Unpublished"').count()
        print(f"\nPublished indicators: {published_count}")
        print(f"Unpublished indicators: {unpublished_count}")

        # Check for description content
        desc_present = "FamiliClaw" in body_text or "Everything your family" in body_text
        print(f"Description content present: {desc_present}")

        # Check for uploaded file
        zip_present = "familiclaw" in body_text.lower() or ".zip" in body_text.lower()
        print(f"ZIP file reference present: {zip_present}")

        # List all buttons
        buttons = page.locator("button")
        btn_count = await buttons.count()
        print(f"\nButtons ({btn_count}):")
        for i in range(min(btn_count, 30)):
            try:
                text = await buttons.nth(i).inner_text()
                visible = await buttons.nth(i).is_visible()
                if visible and text.strip():
                    print(f"  [{i}] '{text.strip()}'")
            except:
                pass

        # Try to publish if not already published
        if unpublished_count > 0 or published_count == 0:
            print("\n=== Attempting to publish product ===")
            # Look for publish toggle/button
            publish_btn = page.locator('button:has-text("Publish")').first
            try:
                await publish_btn.wait_for(timeout=5000)
                btn_text = await publish_btn.inner_text()
                print(f"Found publish button: '{btn_text}'")
                await publish_btn.click()
                await page.wait_for_timeout(3000)
                await page.screenshot(path=str(screenshots_dir / "fc_02_after_publish.png"), full_page=True)
                print(f"After publish URL: {page.url}")
                
                body_after = await page.locator("body").inner_text()
                published_after = await page.locator('text="Published"').count()
                print(f"Published after click: {published_after > 0}")
            except Exception as e:
                print(f"Could not find/click publish button: {e}")
        else:
            print("\n✅ Product appears to be published!")

        print(f"\n🔗 Product URL: https://tenlifejosh.gumroad.com/l/familiclaw")
        print(f"🔗 Edit URL: {EDIT_URL}")

asyncio.run(main())

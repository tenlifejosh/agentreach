"""
Publish the Scripture Memory Cards product on Gumroad (set to published=True).
Also take screenshots to verify state.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault

PRODUCT_ID = "ckdqjk"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
PUBLISH_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit#publish"

async def main():
    vault = SessionVault()
    screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print(f"Navigating to product edit page: {EDIT_URL}")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        await page.screenshot(path=str(screenshots_dir / "01_edit_page.png"))
        print(f"Page title: {await page.title()}")
        print(f"Current URL: {page.url}")

        # Look for publish toggle/button
        # Gumroad has a "Publish" button or toggle in the product edit flow
        # Try to find publish-related elements
        content = await page.content()

        # Check for publish button text
        publish_btn = page.locator('button:has-text("Publish"), a:has-text("Publish"), [data-helper-text*="Publish"]').first
        try:
            await publish_btn.wait_for(timeout=5000)
            print("Found publish button, clicking...")
            await publish_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(screenshots_dir / "02_after_publish_click.png"))
            print(f"After click URL: {page.url}")
        except Exception as e:
            print(f"Publish button not found via text: {e}")

            # Try looking for a toggle or checkbox
            toggle = page.locator('[role="switch"], input[type="checkbox"]').first
            try:
                await toggle.wait_for(timeout=3000)
                is_checked = await toggle.is_checked()
                print(f"Found toggle, checked={is_checked}")
                if not is_checked:
                    await toggle.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=str(screenshots_dir / "03_after_toggle.png"))
                    print("Toggled to published")
            except Exception as e2:
                print(f"Toggle not found: {e2}")

        # Try the publish URL (Gumroad has a dedicated publish section)
        print(f"\nTrying publish section directly...")
        await page.goto(PUBLISH_URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(screenshots_dir / "04_publish_section.png"))

        # Look for "Publish to Gumroad" button
        publish_btns = page.locator('button:has-text("Publish"), button:has-text("publish")')
        count = await publish_btns.count()
        print(f"Found {count} publish-related buttons")
        for i in range(count):
            text = await publish_btns.nth(i).inner_text()
            print(f"  Button {i}: '{text}'")

        # Check for "Published" state
        is_published_text = await page.locator('text="Published"').count()
        print(f"'Published' text found on page: {is_published_text}")

        # Take full page screenshot for review
        await page.screenshot(path=str(screenshots_dir / "05_final_state.png"), full_page=True)

        # Try clicking any "Publish" button we can find
        try:
            btn = page.locator('button:has-text("Publish")').first
            await btn.wait_for(timeout=3000)
            btn_text = await btn.inner_text()
            print(f"\nClicking publish button: '{btn_text}'")
            await btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(screenshots_dir / "06_after_publish.png"))
            print(f"Final URL: {page.url}")

            # Check if published
            published_count = await page.locator('text="Published"').count()
            print(f"'Published' visible after click: {published_count > 0}")
        except Exception as e:
            print(f"Could not click publish: {e}")

asyncio.run(main())

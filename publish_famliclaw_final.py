"""Navigate through wizard and publish FamliClaw."""
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

async def click_save_and_continue(page, step_name):
    """Click Save and continue if present."""
    btn = page.locator('button:has-text("Save and continue")').first
    if await btn.count() > 0 and await btn.is_visible():
        print(f"  [{step_name}] Clicking 'Save and continue'...")
        await btn.click()
        await page.wait_for_timeout(3000)
        return True
    return False

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # Step through wizard tabs: Product → Content → Receipt → Share
        # Each tab may have "Save and continue"
        for step in range(5):
            body = await page.locator("body").inner_text()
            
            # Check if we reached publish button
            pub_btn = page.locator('button:has-text("Publish")').first
            unpub_btn = page.locator('button:has-text("Unpublish")').first
            
            pub_count = await pub_btn.count()
            unpub_count = await unpub_btn.count()
            
            if unpub_count > 0:
                print(f"Step {step}: Product is PUBLISHED ✅")
                break
            
            if pub_count > 0:
                print(f"Step {step}: Found Publish button — clicking!")
                await pub_btn.click()
                await page.wait_for_timeout(4000)
                await page.screenshot(path=str(screenshots_dir / f"publish_step{step}.png"), full_page=True)
                
                # Verify
                unpub_after = await page.locator('button:has-text("Unpublish")').count()
                if unpub_after > 0:
                    print("✅ PUBLISHED SUCCESSFULLY!")
                else:
                    print("Clicked publish, checking state...")
                    body2 = await page.locator("body").inner_text()
                    lines = [l.strip() for l in body2.split('\n') if l.strip()]
                    for line in lines[:20]:
                        print(f"  {line}")
                break
            
            # Try clicking "Save and continue" to advance
            saved = await click_save_and_continue(page, f"step{step}")
            if not saved:
                # Try clicking tab navigation
                # Check for Content tab
                content_tab = page.locator('a:has-text("Content"), button:has-text("Content")').first
                if await content_tab.count() > 0:
                    print(f"Step {step}: Clicking Content tab")
                    await content_tab.click()
                    await page.wait_for_timeout(2000)
                else:
                    print(f"Step {step}: No navigation found, current state:")
                    lines = [l.strip() for l in body.split('\n') if l.strip()]
                    for line in lines[:20]:
                        print(f"  {line}")
                    
                    # List buttons
                    buttons = page.locator("button")
                    btn_count = await buttons.count()
                    for i in range(min(btn_count, 20)):
                        try:
                            text = await buttons.nth(i).inner_text()
                            visible = await buttons.nth(i).is_visible()
                            if visible and text.strip():
                                print(f"  BTN[{i}]: '{text.strip()}'")
                        except:
                            pass
                    break

        # Final check via dashboard
        print("\n=== Final dashboard check ===")
        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        for line in lines[:40]:
            if "famliclaw" in line.lower() or "familiclaw" in line.lower() or "FamliClaw" in line or "FamiliClaw" in line or "Published" in line or "Unpublished" in line:
                print(f"  {line}")
        
        await page.screenshot(path=str(screenshots_dir / "final_dashboard.png"), full_page=True)

asyncio.run(main())

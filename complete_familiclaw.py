"""
Complete FamiliClaw publish flow:
1. Save product page
2. Go to content tab, verify/upload file
3. Publish via "Publish and continue"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

PRODUCT_ID = "fhlmxiz"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
CONTENT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit/content"
FILE_PATH = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/familiclaw-package.zip"

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def screenshot(page: Page, name: str):
    p = screenshots_dir / name
    await page.screenshot(path=str(p), full_page=True)
    print(f"  [screenshot: {name}]")

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        # Step 1: Save product page and continue
        print("=== Step 1: Save product page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "fc_complete_01_edit.png")

        save_btn = page.locator('button:has-text("Save and continue")').first
        try:
            await save_btn.wait_for(timeout=5000)
            print("Clicking 'Save and continue'...")
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(3000)
            print(f"After save URL: {page.url}")
            await screenshot(page, "fc_complete_02_after_save.png")
        except Exception as e:
            print(f"Save button issue: {e}")

        # Step 2: Check content tab
        print("\n=== Step 2: Content tab ===")
        await page.goto(CONTENT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await screenshot(page, "fc_complete_03_content.png")

        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print("Content page (first 50 lines):")
        for line in lines[:50]:
            print(f"  {line}")

        # Check if file is already uploaded
        file_uploaded = "familiclaw" in body.lower() or ".zip" in body.lower()
        print(f"\nFile already uploaded: {file_uploaded}")

        if not file_uploaded:
            print("Need to upload file...")
            # Try to upload
            file_inputs = page.locator('input[type="file"]')
            fi_count = await file_inputs.count()
            print(f"File inputs: {fi_count}")

            upload_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload your files"), button:has-text("Upload")').first
            try:
                await upload_btn.wait_for(timeout=5000)
                print("Found upload button, clicking...")
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(FILE_PATH)
                print("File set in chooser, waiting for upload...")
                await page.wait_for_timeout(15000)
                await screenshot(page, "fc_complete_04_after_upload.png")
            except Exception as e:
                print(f"Upload button approach failed: {e}")
                if fi_count > 0:
                    try:
                        await file_inputs.first.set_input_files(FILE_PATH)
                        print("Direct file input set")
                        await page.wait_for_timeout(15000)
                        await screenshot(page, "fc_complete_04_direct_upload.png")
                    except Exception as e2:
                        print(f"Direct input failed: {e2}")

        # List buttons on content page
        buttons = page.locator("button")
        btn_count = await buttons.count()
        print(f"\nButtons on content page ({btn_count}):")
        for i in range(min(btn_count, 30)):
            try:
                text = await buttons.nth(i).inner_text()
                visible = await buttons.nth(i).is_visible()
                if visible and text.strip():
                    print(f"  [{i}] '{text.strip()}'")
            except:
                pass

        # Step 3: Look for Publish button
        print("\n=== Step 3: Looking for Publish button ===")
        publish_selectors = [
            'button:has-text("Publish and continue")',
            'button:has-text("Publish")',
            'button:has-text("Save and continue")',
        ]

        for sel in publish_selectors:
            btn = page.locator(sel).first
            try:
                await btn.wait_for(timeout=3000)
                btn_text = await btn.inner_text()
                print(f"Found: '{btn_text}' — clicking...")
                await btn.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                print(f"URL after click: {page.url}")
                await screenshot(page, "fc_complete_05_after_publish_click.png")
                break
            except Exception as e:
                print(f"  '{sel}' not found: {e}")

        # Final state
        final_body = await page.locator("body").inner_text()
        final_lines = [l.strip() for l in final_body.split('\n') if l.strip()]
        print("\nFinal page (first 40 lines):")
        for line in final_lines[:40]:
            print(f"  {line}")

        print(f"\n🔗 Product URL: https://tenlifejosh.gumroad.com/l/familiclaw")
        print(f"🔗 Edit URL: {EDIT_URL}")
        print(f"🔗 Current URL: {page.url}")

asyncio.run(main())

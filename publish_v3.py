"""
Complete Gumroad product setup: upload file + publish via "Publish and continue" button.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

PRODUCT_ID = "ckdqjk"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
CONTENT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit/content"
FILE_PATH = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/scripture-memory-cards/scripture-memory-cards.pdf"

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def screenshot(page: Page, name: str):
    p = screenshots_dir / name
    await page.screenshot(path=str(p), full_page=True)
    print(f"  [screenshot: {name}]")

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        # Step 1: Go to content/upload page
        print("=== Step 1: Navigate to Content tab ===")
        await page.goto(CONTENT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "v3_s1_content.png")
        print(f"URL: {page.url}")

        # Step 2: Upload the PDF file  
        print("\n=== Step 2: Upload PDF file ===")
        file_inputs = page.locator('input[type="file"]')
        fi_count = await file_inputs.count()
        print(f"File inputs found: {fi_count}")

        # Click "Upload files" button first to trigger file input
        upload_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload your files")').first
        try:
            await upload_btn.wait_for(timeout=5000)
            print("Found 'Upload files' button")
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                await upload_btn.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(FILE_PATH)
            print("File chooser set")
        except Exception as e:
            print(f"Button click approach failed: {e}")
            # Fall back to direct file input
            if fi_count > 0:
                try:
                    await file_inputs.first.set_input_files(FILE_PATH)
                    print("Direct file input set")
                except Exception as e2:
                    print(f"Direct input also failed: {e2}")

        # Wait for upload to process
        print("Waiting for upload to process...")
        await page.wait_for_timeout(8000)
        await screenshot(page, "v3_s2_after_upload.png")

        # Check if file is uploaded
        page_text = await page.locator("body").inner_text()
        if "scripture-memory-cards" in page_text.lower() or "pdf" in page_text.lower():
            print("File appears to be uploaded!")
        else:
            print("File may not be uploaded, checking page...")

        # List buttons
        buttons = page.locator("button")
        btn_count = await buttons.count()
        print(f"\nButtons visible ({btn_count}):")
        for i in range(min(btn_count, 25)):
            try:
                text = await buttons.nth(i).inner_text()
                visible = await buttons.nth(i).is_visible()
                if visible and text.strip():
                    print(f"  [{i}] '{text.strip()}'")
            except:
                pass

        # Step 3: Click "Publish and continue"
        print("\n=== Step 3: Click 'Publish and continue' ===")
        publish_btn = page.locator('button:has-text("Publish and continue")').first
        try:
            await publish_btn.wait_for(timeout=5000)
            print("Found 'Publish and continue' button, clicking...")
            await publish_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(3000)
            print(f"URL after publish: {page.url}")
            await screenshot(page, "v3_s3_after_publish.png")

            # Show page text
            post_text = await page.locator("body").inner_text()
            lines = [l.strip() for l in post_text.split('\n') if l.strip()]
            print("Post-publish page content (first 40 lines):")
            for line in lines[:40]:
                print(f"  {line}")

        except Exception as e:
            print(f"Publish button failed: {e}")

            # Try Save changes button instead
            save_btn = page.locator('button:has-text("Save changes")').first
            try:
                await save_btn.wait_for(timeout=3000)
                print("Clicking 'Save changes' instead...")
                await save_btn.click()
                await page.wait_for_timeout(3000)
                await screenshot(page, "v3_s3_save.png")
                print(f"URL after save: {page.url}")
            except Exception as e2:
                print(f"Save also failed: {e2}")

asyncio.run(main())

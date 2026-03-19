"""
Navigate Gumroad product edit flow fully — upload file and publish.
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
        print(f"=== Step 1: Navigate to edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "s1_edit.png")

        # Print all buttons on page
        buttons = page.locator("button")
        btn_count = await buttons.count()
        print(f"Buttons on page ({btn_count}):")
        for i in range(min(btn_count, 30)):
            try:
                text = await buttons.nth(i).inner_text()
                visible = await buttons.nth(i).is_visible()
                if visible:
                    print(f"  [{i}] '{text.strip()}'")
            except:
                pass

        # Look at all tabs
        tabs = page.locator('[role="tab"], a[href*="/edit"]')
        tab_count = await tabs.count()
        print(f"\nTabs ({tab_count}):")
        for i in range(tab_count):
            try:
                text = await tabs.nth(i).inner_text()
                href = await tabs.nth(i).get_attribute("href")
                print(f"  [{i}] '{text.strip()}' href={href}")
            except:
                pass

        print("\n=== Step 2: Click Save and continue ===")
        save_btn = page.locator('button:has-text("Save and continue")').first
        try:
            await save_btn.wait_for(timeout=5000)
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            print(f"URL after save: {page.url}")
            await screenshot(page, "s2_after_save.png")
        except Exception as e:
            print(f"Save button issue: {e}")

        # What page are we on?
        buttons2 = page.locator("button")
        btn_count2 = await buttons2.count()
        print(f"\nButtons after save ({btn_count2}):")
        for i in range(min(btn_count2, 30)):
            try:
                text = await buttons2.nth(i).inner_text()
                visible = await buttons2.nth(i).is_visible()
                if visible and text.strip():
                    print(f"  [{i}] '{text.strip()}'")
            except:
                pass

        print("\n=== Step 3: Look for Content/Upload tab ===")
        content_tab = page.locator('a:has-text("Content"), button:has-text("Content"), [href*="content"]').first
        try:
            await content_tab.wait_for(timeout=3000)
            await content_tab.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            print(f"URL: {page.url}")
            await screenshot(page, "s3_content.png")
        except Exception as e:
            print(f"No content tab: {e}")

        print("\n=== Step 4: Look for file upload ===")
        file_inputs = page.locator('input[type="file"]')
        fi_count = await file_inputs.count()
        print(f"File inputs: {fi_count}")
        if fi_count > 0:
            print("Uploading file...")
            await file_inputs.first.set_input_files(FILE_PATH)
            await page.wait_for_timeout(5000)
            await screenshot(page, "s4_file_uploaded.png")
            print("File input set")

        print("\n=== Step 5: Look for publish/for sale toggle ===")
        # Gumroad uses a specific "for sale" toggle
        for_sale = page.locator('[data-testid*="publish"], [aria-label*="published"], [aria-label*="sale"]').first
        try:
            await for_sale.wait_for(timeout=3000)
            print(f"Found for-sale element")
            await for_sale.click()
            await page.wait_for_timeout(2000)
        except:
            pass

        # Check page HTML for any mention of published/for sale
        html = await page.content()
        if "for sale" in html.lower():
            print("'for sale' found in HTML")
        if "published" in html.lower():
            print("'published' found in HTML")

        # Navigate to Share tab (has publish toggle in Gumroad)
        print("\n=== Step 6: Try Share tab ===")
        await page.goto(f"https://gumroad.com/products/{PRODUCT_ID}/edit", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        share_tab = page.locator('a:has-text("Share"), a[href*="share"]').first
        try:
            await share_tab.wait_for(timeout=3000)
            await share_tab.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_timeout(2000)
            print(f"Share URL: {page.url}")
            await screenshot(page, "s6_share.png")
        except Exception as e:
            print(f"No share tab: {e}")

        # Final: look for any "Publish" text or control
        print("\n=== Step 7: Search for publish controls ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)

        # Print visible text on page to understand what's there
        body_text = await page.locator("body").inner_text()
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        print("Page text (first 80 lines):")
        for line in lines[:80]:
            print(f"  {line}")

asyncio.run(main())

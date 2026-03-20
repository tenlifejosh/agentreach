"""
Debug - detailed inspection of pin editor panel after upload
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agentreach.browser.session import platform_context

TEST_IMAGE = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-1-hero.jpg"

async def main():
    async with platform_context("pinterest", headless=True) as (ctx, page):
        await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Click "Create new" first
        create_btn = page.locator('[data-test-id="storyboard-create-button"]').first
        if await create_btn.count() > 0:
            await create_btn.click()
            await page.wait_for_timeout(2000)
        
        # Upload image directly
        file_input = page.locator('#storyboard-upload-input').first
        await file_input.set_input_files(TEST_IMAGE)
        await page.wait_for_timeout(6000)  # wait longer for upload to complete
        
        print("URL after upload:", page.url)
        
        # Dump ALL data-test-id elements - looking for board/publish
        print("\n=== ALL DATA-TEST-IDs ===")
        test_ids = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id]');
                return Array.from(els).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    text: (el.innerText || '').substring(0, 50).replace(/\\n/g, '|'),
                    visible: window.getComputedStyle(el).display !== 'none' && window.getComputedStyle(el).visibility !== 'hidden',
                }));
            }
        """)
        for el in test_ids:
            print(el)
        
        # Check if the new draft was created and selected
        print("\n=== DRAFT COUNT ===")
        draft_count = await page.evaluate("""
            () => {
                const drafts = document.querySelectorAll('[data-test-id^="pinDraft-"]');
                return drafts.length;
            }
        """)
        print(f"Draft count: {draft_count}")
        
        # Click on the most recent draft to open editor
        print("\nClicking most recent draft...")
        recent_draft = page.locator('[data-test-id^="pinDraft-"]').last
        if await recent_draft.count() > 0:
            await recent_draft.click()
            await page.wait_for_timeout(3000)
        
        print("\n=== ALL DATA-TEST-IDs AFTER CLICKING DRAFT ===")
        test_ids2 = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id]');
                return Array.from(els).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    text: (el.innerText || '').substring(0, 50).replace(/\\n/g, '|'),
                }));
            }
        """)
        for el in test_ids2:
            print(el)

if __name__ == "__main__":
    asyncio.run(main())

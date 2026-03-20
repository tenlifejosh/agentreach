"""
Debug - click Create Board in dropdown and inspect
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
        
        # Upload image
        file_input = page.locator('#storyboard-upload-input').first
        await file_input.set_input_files(TEST_IMAGE)
        await page.wait_for_timeout(5000)
        
        # Click board dropdown
        board_btn = page.locator('[data-test-id="board-dropdown-select-button"]').first
        await board_btn.click()
        await page.wait_for_timeout(1500)
        
        # Click "Create board"
        create_board_btn = page.locator('[data-test-id="create-board-button"]').first
        print(f"Create board button count: {await create_board_btn.count()}")
        if await create_board_btn.count() > 0:
            await create_board_btn.click()
            await page.wait_for_timeout(2000)
        
        # Dump all inputs and test ids
        print("\n=== INPUTS AFTER CLICKING CREATE BOARD ===")
        inputs = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('input, textarea, [contenteditable="true"]');
                return Array.from(els).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    type: el.type,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    dataTestId: el.getAttribute('data-test-id'),
                    visible: window.getComputedStyle(el).display !== 'none' && window.getComputedStyle(el).visibility !== 'hidden',
                }));
            }
        """)
        for inp in inputs:
            print(inp)
        
        print("\n=== DATA TEST IDs AFTER CLICKING CREATE BOARD ===")
        test_ids = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id]');
                return Array.from(els).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    text: (el.innerText || '').substring(0, 60).replace(/\\n/g, '|'),
                }));
            }
        """)
        for el in test_ids:
            print(el)

if __name__ == "__main__":
    asyncio.run(main())

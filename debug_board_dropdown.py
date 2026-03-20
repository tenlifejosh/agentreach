"""
Debug - check board dropdown after upload
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
        print(f"Board button count: {await board_btn.count()}")
        if await board_btn.count() > 0:
            await board_btn.click()
            await page.wait_for_timeout(2000)
            
            # Dump what appears
            all_els = await page.evaluate("""
                () => {
                    const els = document.querySelectorAll('[role="option"], [role="listbox"], [role="list"], [role="listitem"], [data-test-id]');
                    return Array.from(els).map(el => ({
                        tag: el.tagName,
                        role: el.getAttribute('role'),
                        testId: el.getAttribute('data-test-id'),
                        text: (el.innerText || '').substring(0, 60).replace(/\\n/g, '|'),
                        class: el.className.substring(0, 60),
                    })).slice(0, 50);
                }
            """)
            for el in all_els:
                print(el)
        
        print("\n=== ALL INPUTS AFTER DROPDOWN ===")
        inputs = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input, [contenteditable="true"]');
                return Array.from(inputs).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    type: el.type,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    visible: window.getComputedStyle(el).display !== 'none',
                }));
            }
        """)
        for inp in inputs:
            print(inp)

if __name__ == "__main__":
    asyncio.run(main())

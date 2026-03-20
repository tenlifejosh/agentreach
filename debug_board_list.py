"""
Debug - check full board dropdown list DOM
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
        await page.wait_for_timeout(2000)
        
        # Get ALL elements in the board picker
        board_list = await page.evaluate("""
            () => {
                // Find the picker container
                const picker = document.querySelector('#pickerSearchField');
                const container = picker ? picker.closest('[class*="picker"], [class*="dropdown"], [class*="Picker"]') : null;
                
                if (!container) {
                    // Just dump all visible elements with board-related text
                    const all = document.querySelectorAll('*');
                    const results = [];
                    for (const el of all) {
                        const text = (el.innerText || '');
                        if (el.children.length === 0 && text.length > 0 && text.length < 80) {
                            results.push({
                                tag: el.tagName,
                                id: el.id,
                                dataTestId: el.getAttribute('data-test-id'),
                                text: text,
                                class: el.className.substring(0, 60),
                            });
                        }
                    }
                    return results.slice(0, 50);
                }
                
                const els = container.querySelectorAll('*');
                return Array.from(els).slice(0, 80).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    dataTestId: el.getAttribute('data-test-id'),
                    text: (el.innerText || '').substring(0, 60).replace(/\\n/g, '|'),
                    class: el.className.substring(0, 60),
                    role: el.getAttribute('role'),
                }));
            }
        """)
        print("=== BOARD LIST DOM ===")
        for el in board_list:
            print(el)
        
        # Also dump data-test-ids that contain "board" after dropdown opens
        print("\n=== BOARD TEST IDs IN DROPDOWN ===")
        board_test_ids = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id*="board"], [data-test-id*="Board"]');
                return Array.from(els).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    text: (el.innerText || '').substring(0, 80).replace(/\\n/g, '|'),
                    role: el.getAttribute('role'),
                }));
            }
        """)
        for el in board_test_ids:
            print(el)

if __name__ == "__main__":
    asyncio.run(main())

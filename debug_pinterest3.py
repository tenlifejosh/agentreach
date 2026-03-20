"""
Debug - upload image, fill fields, check board selector
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
        
        # Click "Create new"
        create_btn = page.locator('[data-test-id="storyboard-create-button"]').first
        if await create_btn.count() > 0:
            await create_btn.click()
            await page.wait_for_timeout(2000)
        
        # Upload image directly to the file input
        print("Uploading image...")
        file_input = page.locator('#storyboard-upload-input').first
        if await file_input.count() > 0:
            await file_input.set_input_files(TEST_IMAGE)
            print("set_input_files called")
        else:
            print("File input not found!")
        await page.wait_for_timeout(4000)
        
        # Check state after upload
        print("\nURL:", page.url)
        
        # Try filling title
        title_input = page.locator('#storyboard-selector-title').first
        if await title_input.count() > 0:
            await title_input.fill("Test Pin Title")
            print("Title filled!")
        else:
            print("Title input not found")
        
        # Try filling description
        desc_div = page.locator('[aria-label="Add a detailed description"]').first
        if await desc_div.count() > 0:
            await desc_div.click()
            await page.wait_for_timeout(200)
            await desc_div.fill("Test description text")
            print("Description filled!")
        else:
            print("Description div not found")
        
        # Try link
        link_input = page.locator('#WebsiteField').first
        if await link_input.count() > 0:
            await link_input.fill("https://example.com")
            print("Link filled!")
        else:
            print("Link input not found")
        
        # Check board selector
        print("\n=== BOARD SELECTOR ===")
        board_state = await page.evaluate("""
            () => {
                const selectors = [
                    '[data-test-id="board-dropdown-select-btn"]',
                    '[data-test-id*="board"]',
                    '[aria-label*="board" i]',
                    '[aria-label*="Board" i]',
                    '[data-test-id*="Board"]',
                ];
                const results = [];
                for (const sel of selectors) {
                    try {
                        const els = document.querySelectorAll(sel);
                        for (const el of Array.from(els).slice(0, 5)) {
                            results.push({
                                selector: sel,
                                tag: el.tagName,
                                id: el.id,
                                dataTestId: el.getAttribute('data-test-id'),
                                text: (el.innerText || '').substring(0, 60),
                                ariaLabel: el.getAttribute('aria-label'),
                            });
                        }
                    } catch(e) {}
                }
                return results.slice(0, 20);
            }
        """)
        for b in board_state:
            print(b)
        
        # Check publish buttons
        print("\n=== PUBLISH BUTTONS ===")
        pub_state = await page.evaluate("""
            () => {
                const selectors = [
                    '[data-test-id*="publish"]',
                    '[data-test-id*="save"]',
                    '[data-test-id*="submit"]',
                ];
                const results = [];
                for (const sel of selectors) {
                    try {
                        const els = document.querySelectorAll(sel);
                        for (const el of Array.from(els).slice(0, 5)) {
                            results.push({
                                selector: sel,
                                tag: el.tagName,
                                dataTestId: el.getAttribute('data-test-id'),
                                text: (el.innerText || '').substring(0, 40),
                                disabled: el.disabled,
                            });
                        }
                    } catch(e) {}
                }
                return results.slice(0, 20);
            }
        """)
        for p in pub_state:
            print(p)

if __name__ == "__main__":
    asyncio.run(main())

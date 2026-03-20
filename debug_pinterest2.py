"""
Debug - inspect the pin editor AFTER clicking Create New
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
        await page.wait_for_timeout(3000)
        
        print("URL:", page.url)
        
        # Click "Create new" button
        create_btn = page.locator('[data-test-id="storyboard-create-button"]').first
        if await create_btn.count() > 0:
            print("Clicking 'Create new'...")
            await create_btn.click()
            await page.wait_for_timeout(3000)
        else:
            print("No 'Create new' button found")
        
        print("\nURL after click:", page.url)
        
        # Now check for upload areas
        print("\n=== FILE INPUTS ===")
        file_inputs = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('input[type="file"]');
                return Array.from(els).map(el => ({
                    id: el.id,
                    class: el.className.substring(0, 80),
                    accept: el.accept,
                    dataTestId: el.getAttribute('data-test-id'),
                    visible: el.offsetParent !== null,
                    display: window.getComputedStyle(el).display,
                    opacity: window.getComputedStyle(el).opacity,
                }));
            }
        """)
        for fi in file_inputs:
            print(fi)
        
        # Check for upload zones / drop targets
        print("\n=== UPLOAD/DROP ZONES ===")
        upload_zones = await page.evaluate("""
            () => {
                const selectors = [
                    '[data-test-id*="upload"]',
                    '[class*="Upload"]',
                    '[class*="upload"]',
                    '[class*="drop"]',
                    '[class*="Drop"]',
                    '[aria-label*="upload" i]',
                    'button:has-text("Upload")',
                ];
                const results = [];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        results.push({
                            selector: sel,
                            tag: el.tagName,
                            id: el.id,
                            dataTestId: el.getAttribute('data-test-id'),
                            ariaLabel: el.getAttribute('aria-label'),
                            text: el.innerText?.substring(0, 40),
                            class: el.className.substring(0, 60),
                        });
                    }
                }
                return results.slice(0, 30);
            }
        """)
        for z in upload_zones:
            print(z)
        
        # Check for board selector
        print("\n=== BOARD SELECTOR ===")
        board_els = await page.evaluate("""
            () => {
                const selectors = [
                    '[data-test-id*="board"]',
                    '[aria-label*="board" i]',
                    'button:has-text("Board")',
                    '[class*="board" i]',
                ];
                const results = [];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        results.push({
                            selector: sel,
                            tag: el.tagName,
                            id: el.id,
                            dataTestId: el.getAttribute('data-test-id'),
                            text: el.innerText?.substring(0, 60),
                            ariaLabel: el.getAttribute('aria-label'),
                        });
                    }
                }
                return results.slice(0, 20);
            }
        """)
        for b in board_els:
            print(b)
        
        # Check for publish/save button
        print("\n=== PUBLISH/SAVE BUTTONS ===")
        pub_els = await page.evaluate("""
            () => {
                const selectors = [
                    '[data-test-id*="publish"]',
                    '[data-test-id*="save"]',
                    'button:has-text("Publish")',
                    'button:has-text("Save")',
                    '[data-test-id*="submit"]',
                ];
                const results = [];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        results.push({
                            selector: sel,
                            tag: el.tagName,
                            dataTestId: el.getAttribute('data-test-id'),
                            text: el.innerText?.substring(0, 40),
                            disabled: el.disabled,
                        });
                    }
                }
                return results.slice(0, 20);
            }
        """)
        for p in pub_els:
            print(p)
        
        # Dump all data-test-id elements after "Create new"
        print("\n=== ALL DATA-TEST-IDS (after Create New) ===")
        test_ids = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id]');
                return Array.from(els).slice(0, 80).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    text: el.innerText?.substring(0, 40),
                }));
            }
        """)
        for el in test_ids:
            print(el)

if __name__ == "__main__":
    asyncio.run(main())

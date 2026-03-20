"""
Debug script to inspect Pinterest pin creation tool DOM after image upload.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agentreach.browser.session import platform_context
from src.agentreach.browser.uploader import upload_file

TEST_IMAGE = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-1-hero.jpg"

async def main():
    async with platform_context("pinterest", headless=False) as (ctx, page):
        await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        
        print("=== PAGE URL ===")
        print(page.url)
        
        # Try to upload image
        print("\n=== UPLOADING IMAGE ===")
        uploaded = await upload_file(
            page,
            TEST_IMAGE,
            trigger_selector='[data-test-id="storyboard-upload-input"], [class*="upload"]',
            input_selector='input[type="file"]',
        )
        print(f"Upload result: {uploaded}")
        await page.wait_for_timeout(4000)
        
        # Dump relevant elements
        print("\n=== INPUT ELEMENTS ===")
        inputs = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"], [role="textbox"]');
                return Array.from(inputs).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    name: el.name,
                    type: el.type,
                    placeholder: el.placeholder,
                    class: el.className.substring(0, 80),
                    dataTestId: el.getAttribute('data-test-id'),
                    ariaLabel: el.getAttribute('aria-label'),
                    role: el.getAttribute('role'),
                    contentEditable: el.getAttribute('contenteditable'),
                    visible: el.offsetParent !== null,
                }));
            }
        """)
        for inp in inputs:
            print(inp)
        
        print("\n=== DATA-TEST-ID ELEMENTS ===")
        test_ids = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[data-test-id]');
                return Array.from(els).slice(0, 60).map(el => ({
                    tag: el.tagName,
                    testId: el.getAttribute('data-test-id'),
                    role: el.getAttribute('role'),
                    text: el.innerText?.substring(0, 40),
                    contentEditable: el.getAttribute('contenteditable'),
                }));
            }
        """)
        for el in test_ids:
            print(el)
        
        # Wait to see the state
        await page.wait_for_timeout(2000)

if __name__ == "__main__":
    asyncio.run(main())

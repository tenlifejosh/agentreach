"""
Debug KDP - find how to get to the new paperback form via the bookshelf Create button.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.browser.session import platform_context


async def main():
    async with platform_context("kdp", headless=True) as (ctx, page):
        print("Going to bookshelf...")
        await page.goto("https://kdp.amazon.com/en_US/bookshelf", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"URL: {page.url}")
        
        # Take screenshot
        await page.screenshot(path="/tmp/kdp_bookshelf.png")
        print("Screenshot: /tmp/kdp_bookshelf.png")
        
        # Find all buttons and links on the bookshelf page
        buttons = await page.eval_on_selector_all('button, a[href*="paperback"], a[href*="title"]', """
            els => els.map(el => ({
                tag: el.tagName,
                text: el.textContent.trim().substring(0, 80),
                href: el.href || '',
                class: el.className.substring(0, 60)
            })).filter(el => el.text.length > 0)
        """)
        
        print(f"\nButtons/links ({len(buttons)}):")
        for b in buttons[:30]:
            print(f"  [{b['tag']}] '{b['text']}' href={b.get('href', '')[:80]}")
        
        # Find "Create" or "Add" buttons
        create_btns = await page.eval_on_selector_all(
            'button:has-text("Create"), a:has-text("Create"), button:has-text("Add new"), [data-action*="create"]', 
            'els => els.map(el => ({tag: el.tagName, text: el.textContent.trim(), href: el.href || ""}))'
        )
        print(f"\nCreate buttons: {create_btns}")
        
        # Try clicking the "Create a New Title" or "Paperback" button
        # Look for the dropdown or menu
        # In KDP, there's usually a "+ Create" button
        try:
            create_btn = page.locator('button:has-text("Create"), a:has-text("Create a new title")').first
            count = await create_btn.count()
            print(f"\nCreate button count: {count}")
            if count > 0:
                print("Clicking create button...")
                await create_btn.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path="/tmp/kdp_after_create.png")
                print(f"URL after create click: {page.url}")
                
                # Look for paperback option
                pb_btns = await page.eval_on_selector_all(
                    'button:has-text("Paperback"), a:has-text("Paperback")',
                    'els => els.map(el => ({tag: el.tagName, text: el.textContent.trim(), href: el.href || ""}))'
                )
                print(f"Paperback buttons: {pb_btns}")
                
                if pb_btns:
                    pb_btn = page.locator('button:has-text("Paperback"), a:has-text("Paperback")').first
                    await pb_btn.click()
                    await page.wait_for_timeout(3000)
                    print(f"URL after paperback click: {page.url}")
                    await page.screenshot(path="/tmp/kdp_paperback_form.png")
                    
                    # Check for title field
                    title_el = await page.query_selector('[id*="title"], input[placeholder*="title" i]')
                    print(f"Title field found: {title_el is not None}")
                    if title_el:
                        print(f"Title field ID: {await page.evaluate('el => el.id', title_el)}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Also try navigating to a specific URL pattern that might work
        print("\n\nTrying alternative URL approach...")
        # Try navigating to the new paperback page via relative link from bookshelf
        links = await page.eval_on_selector_all('a[href*="paperback"], a[href*="setup"], a[href*="new"]', """
            els => els.map(el => ({href: el.href, text: el.textContent.trim().substring(0, 50)}))
        """)
        print(f"Relevant links: {links[:10]}")


asyncio.run(main())

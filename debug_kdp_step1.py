"""
Debug KDP Step 1 page - find correct selectors for the title/author fields.
"""
import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault


async def main():
    vault = SessionVault()
    url = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details"
    
    print(f"Navigating to: {url}")
    
    async with platform_context("kdp", vault, headless=True) as (ctx, page):
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        
        print(f"Current URL: {page.url}")
        print(f"Page title: {await page.title()}")
        
        # Take screenshot
        await page.screenshot(path="/tmp/kdp_step1_debug.png", full_page=True)
        print("Screenshot saved to /tmp/kdp_step1_debug.png")
        
        # Find all inputs with IDs
        inputs = await page.eval_on_selector_all('input, textarea, select', """
            els => els.map(el => ({
                tag: el.tagName,
                id: el.id,
                name: el.name,
                type: el.type,
                placeholder: el.placeholder,
                class: el.className.substring(0, 80)
            }))
        """)
        
        print(f"\nFound {len(inputs)} form elements:")
        for inp in inputs:
            if inp.get('id') or inp.get('name') or inp.get('placeholder'):
                print(f"  {inp['tag']} id={inp.get('id', '')} name={inp.get('name', '')} "
                      f"type={inp.get('type', '')} placeholder={inp.get('placeholder', '')[:40]}")
        
        # Look for all elements with 'title' in their ID
        title_els = await page.eval_on_selector_all('[id*="title"], [name*="title"]', """
            els => els.map(el => ({
                tag: el.tagName,
                id: el.id,
                name: el.name,
                type: el.type,
                class: el.className.substring(0, 80),
                visible: el.offsetParent !== null
            }))
        """)
        print(f"\nElements with 'title' in id/name ({len(title_els)}):")
        for el in title_els:
            print(f"  {el}")
        
        # Also check for any label text that mentions "title"
        labels = await page.eval_on_selector_all('label', """
            els => els.map(el => ({
                for: el.htmlFor,
                text: el.textContent.trim().substring(0, 80)
            })).filter(l => l.text.length > 0)
        """)
        print(f"\nLabels ({len(labels)}):")
        for label in labels[:30]:
            print(f"  {label}")
        
        # Get the page HTML title elements
        h_els = await page.eval_on_selector_all('h1, h2, h3, h4', """
            els => els.map(el => el.textContent.trim().substring(0, 100))
        """)
        print(f"\nHeadings: {h_els[:10]}")
        
        # Check for any loading state
        loading = await page.eval_on_selector_all('[class*="loading"], [class*="spinner"]', """
            els => els.map(el => ({class: el.className.substring(0, 80), visible: el.offsetParent !== null}))
        """)
        print(f"\nLoading elements: {loading}")
        
        # Wait more and try again
        print("\nWaiting 5 more seconds...")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="/tmp/kdp_step1_debug2.png", full_page=True)
        print("Screenshot 2 saved to /tmp/kdp_step1_debug2.png")
        
        # Re-check URL
        print(f"URL after wait: {page.url}")
        
        # Check if page has a React root
        react_root = await page.evaluate("""
            () => {
                const root = document.getElementById('root') || document.querySelector('[data-reactroot]');
                return root ? 'React root found' : 'No React root';
            }
        """)
        print(f"React: {react_root}")
        
        # Get all data-* attributes that have book-related names
        data_attrs = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('[id]').forEach(el => {
                    if (el.id.includes('print') || el.id.includes('book') || el.id.includes('title') || 
                        el.id.includes('author') || el.id.includes('description')) {
                        results.push({id: el.id, tag: el.tagName, visible: el.offsetParent !== null});
                    }
                });
                return results;
            }
        """)
        print(f"\nBook-related IDs ({len(data_attrs)}):")
        for el in data_attrs:
            print(f"  {el}")
        
        # Try waiting for network idle then check again
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
            print("\nNetwork idle reached")
        except Exception as e:
            print(f"\nNetwork idle timeout: {e}")
        
        await page.screenshot(path="/tmp/kdp_step1_debug3.png", full_page=True)
        print("Screenshot 3 saved to /tmp/kdp_step1_debug3.png")
        
        final_url = page.url
        print(f"\nFinal URL: {final_url}")
        
        # Re-search for title input
        title_check = await page.eval_on_selector_all('[id*="title"], input[placeholder*="title" i]', """
            els => els.map(el => ({id: el.id, name: el.name, placeholder: el.placeholder}))
        """)
        print(f"Final title elements: {title_check}")


asyncio.run(main())

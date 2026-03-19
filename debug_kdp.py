"""
KDP Form Debug Script
Navigates to KDP new paperback form, takes screenshots, and discovers selectors.
"""
import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.browser.session import platform_context


async def debug_kdp_form():
    screenshots_dir = Path(__file__).parent / "debug_screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    print("=== KDP FORM DEBUG ===")
    print("Opening authenticated KDP session...")

    async with platform_context("kdp", headless=True, check_health=False) as (ctx, page):
        # Navigate to the KDP new paperback details page
        url = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details"
        print(f"\n[1] Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Screenshot 1: Initial page state
        ss1 = str(screenshots_dir / "01_initial_load.png")
        await page.screenshot(path=ss1, full_page=True)
        print(f"    ✓ Screenshot saved: {ss1}")
        print(f"    Current URL: {page.url}")
        print(f"    Page title: {await page.title()}")

        # Check if we got redirected to signin
        if "signin" in page.url or "ap/signin" in page.url:
            print("    ⚠ REDIRECTED TO SIGN-IN — session may be expired!")
            return

        # Wait for the form to be fully loaded
        print("\n[2] Waiting for form elements...")
        try:
            await page.wait_for_selector("input, textarea, select", timeout=15000)
        except Exception as e:
            print(f"    No form elements found within 15s: {e}")

        await page.wait_for_timeout(2000)

        # Screenshot 2: After wait
        ss2 = str(screenshots_dir / "02_after_wait.png")
        await page.screenshot(path=ss2, full_page=True)
        print(f"    ✓ Screenshot: {ss2}")

        # Enumerate all form fields
        print("\n[3] Enumerating all form fields...")
        fields_js = """
        () => {
            const fields = [];
            const inputs = document.querySelectorAll('input, textarea, select');
            inputs.forEach(el => {
                fields.push({
                    tag: el.tagName,
                    id: el.id || '',
                    name: el.name || '',
                    type: el.type || '',
                    placeholder: el.placeholder || '',
                    'class': (el.className || '').substring(0, 100),
                    'data-a-input-name': el.getAttribute('data-a-input-name') || '',
                    'aria-label': el.getAttribute('aria-label') || '',
                    'aria-labelledby': el.getAttribute('aria-labelledby') || '',
                    value: el.value ? el.value.substring(0, 50) : '',
                    visible: el.offsetParent !== null
                });
            });
            return fields;
        }
        """
        fields = await page.evaluate(fields_js)
        print(f"    Found {len(fields)} form fields:")
        for f in fields:
            if f['visible']:  # Show visible fields first
                print(f"    [VISIBLE] tag={f['tag']} id='{f['id']}' name='{f['name']}' type='{f['type']}' placeholder='{f['placeholder']}' aria-label='{f['aria-label']}' class='{f['class'][:60]}'")

        print("\n    --- All fields (including hidden) ---")
        for f in fields:
            print(f"    tag={f['tag']} id='{f['id']}' name='{f['name']}' type='{f['type']}' placeholder='{f['placeholder']}' aria-label='{f['aria-label']}' data-a-input-name='{f['data-a-input-name']}'")

        # Save fields to JSON for reference
        fields_file = screenshots_dir / "fields.json"
        with open(fields_file, "w") as fh:
            json.dump(fields, fh, indent=2)
        print(f"\n    Fields saved to: {fields_file}")

        # Get all labels and their for= attributes
        print("\n[4] Enumerating all labels...")
        labels_js = """
        () => {
            const labels = [];
            document.querySelectorAll('label').forEach(el => {
                labels.push({
                    for: el.htmlFor || '',
                    text: el.innerText.substring(0, 80),
                    id: el.id || ''
                });
            });
            return labels;
        }
        """
        labels = await page.evaluate(labels_js)
        for lb in labels:
            print(f"    label for='{lb['for']}' text='{lb['text'][:60]}'")

        # Try to find title-related elements specifically
        print("\n[5] Searching for title/subtitle/author fields specifically...")

        # Check various common KDP selectors
        selectors_to_test = [
            # Title selectors
            '#data-print-book-title',
            'input[id*="title"]',
            'input[name*="title"]',
            'input[placeholder*="itle"]',
            '[data-a-input-name*="title"]',
            # Subtitle
            '#data-print-book-subtitle',
            'input[id*="subtitle"]',
            # Author
            'input[id*="first"]',
            'input[id*="last"]',
            'input[placeholder*="irst"]',
            'input[placeholder*="ast"]',
            # Description
            'textarea[id*="description"]',
            'textarea[id*="desc"]',
            '#data-print-book-description',
            # Keywords
            'input[id*="keyword"]',
            # Generic
            'input[type="text"]',
            'textarea',
        ]

        for sel in selectors_to_test:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    # Get details of first match
                    el = page.locator(sel).first
                    el_id = await el.get_attribute("id") or ""
                    el_name = await el.get_attribute("name") or ""
                    el_ph = await el.get_attribute("placeholder") or ""
                    el_vis = await el.is_visible()
                    print(f"    ✓ FOUND {count}x '{sel}' | id='{el_id}' name='{el_name}' placeholder='{el_ph}' visible={el_vis}")
                else:
                    print(f"    ✗ NOT FOUND: '{sel}'")
            except Exception as e:
                print(f"    ERROR checking '{sel}': {e}")

        # Try filling the title field
        print("\n[6] Attempting to fill title field...")
        title_selectors = [
            '#data-print-book-title',
            'input[id*="title"]:not([id*="series"]):not([id*="sub"])',
            'input[name*="title"]:not([name*="subtitle"])',
        ]

        title_filled = False
        for sel in title_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.fill("Pray Bold: Teen Edition")
                    await page.wait_for_timeout(500)
                    val = await loc.input_value()
                    if val:
                        print(f"    ✓ Title filled with selector: '{sel}' — value='{val}'")
                        title_filled = True
                        break
                    else:
                        print(f"    ✗ Filled but empty with: '{sel}'")
            except Exception as e:
                print(f"    ✗ Failed with '{sel}': {e}")

        if not title_filled:
            print("    ⚠ Could not fill title field — need to inspect page HTML")

        # Screenshot 3: After attempting to fill title
        ss3 = str(screenshots_dir / "03_after_title_fill.png")
        await page.screenshot(path=ss3, full_page=True)
        print(f"    ✓ Screenshot: {ss3}")

        # Get full page HTML for deep inspection
        print("\n[7] Saving full page HTML for inspection...")
        html = await page.content()
        html_file = screenshots_dir / "page.html"
        with open(html_file, "w") as fh:
            fh.write(html)
        print(f"    HTML saved: {html_file} ({len(html)} chars)")

        # Search for specific patterns in HTML
        print("\n[8] Searching HTML for key patterns...")
        search_terms = [
            'data-print-book-title',
            'data-print-book-subtitle',
            'data-print-book-description',
            'author',
            'contributor',
            'first-name',
            'last-name',
            'keyword',
            'description',
        ]
        for term in search_terms:
            count = html.lower().count(term.lower())
            if count > 0:
                # Find the context around first occurrence
                idx = html.lower().find(term.lower())
                context = html[max(0, idx-100):idx+200].replace('\n', ' ')
                print(f"    '{term}' found {count}x — first occurrence context:")
                print(f"       ...{context}...")
            else:
                print(f"    '{term}' — NOT FOUND in HTML")

        print("\n=== DEBUG COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(debug_kdp_form())

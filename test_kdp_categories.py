"""
KDP Category exploration — extract all category options and navigate the picker.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from agentreach.browser.session import platform_context

SCREENSHOTS = Path(__file__).parent / "category_screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


async def ss(page, name):
    p = str(SCREENSHOTS / f"{name}.png")
    await page.screenshot(path=p, full_page=False)
    print(f"  📸 {name}")


async def run():
    async with platform_context("kdp", headless=True, check_health=False) as (ctx, page):
        await page.goto(
            "https://kdp.amazon.com/en_US/title-setup/paperback/new/details",
            wait_until="domcontentloaded", timeout=60000
        )
        await page.wait_for_selector('#data-print-book-title', timeout=20000)
        await page.wait_for_timeout(1500)

        # Fill just enough to enable categories
        await page.locator('#data-print-book-title').fill("Test Book")
        await page.locator('#data-print-book-primary-author-first-name').fill("Joshua")
        await page.locator('#data-print-book-primary-author-last-name').fill("Noreen")

        # Set language via JS (Amazon custom dropdown hides the native select)
        lang_result = await page.evaluate("""
            () => {
                const sel = document.getElementById('data-print-book-language-native');
                if (!sel) return 'not_found';
                // Set value directly
                const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value');
                if (nativeSet && nativeSet.set) nativeSet.set.call(sel, 'english');
                else sel.value = 'english';
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                return 'set_' + sel.value;
            }
        """)
        print(f"Language: {lang_result}")

        # Select adult content = No
        await page.evaluate("""
            () => {
                const radio = document.querySelector('input[name="data[print_book][is_adult_content]-radio"][value="false"]');
                if (radio) {
                    radio.click();
                    ['change','input'].forEach(e => radio.dispatchEvent(new Event(e, {bubbles:true})));
                }
            }
        """)
        await page.wait_for_timeout(1000)

        # Wait for categories button to enable
        try:
            await page.wait_for_selector('#categories-modal-button:not([disabled])', timeout=5000)
        except Exception:
            # Force enable
            await page.evaluate("""
                () => {
                    const btn = document.getElementById('categories-modal-button');
                    if (btn) btn.disabled = false;
                }
            """)

        # Open category modal
        await page.locator('#categories-modal-button').click(timeout=5000)
        await page.wait_for_timeout(2000)
        await ss(page, "01_modal_open")

        # Extract ALL options from the first category dropdown
        all_opts = await page.evaluate("""
            () => {
                const results = {};
                document.querySelectorAll('select').forEach(s => {
                    if (s.offsetParent !== null) {
                        const key = s.id || s.name || s.className.substring(0, 30);
                        results[key] = Array.from(s.options).map(o => ({v: o.value, t: o.text.trim()}));
                    }
                });
                return results;
            }
        """)

        print("\n=== VISIBLE SELECT OPTIONS ===")
        for sel_key, opts in all_opts.items():
            print(f"\nSelect: '{sel_key}' ({len(opts)} options)")
            for o in opts:
                print(f"  val='{o['v']}' | '{o['t']}'")

        # Find the category select (the one with JSON values)
        category_sel_key = None
        category_opts = []
        for sel_key, opts in all_opts.items():
            for o in opts:
                if '"nodeId"' in o['v'] or '"level"' in o['v']:
                    category_sel_key = sel_key
                    category_opts = opts
                    break
            if category_sel_key:
                break

        print(f"\nCategory select key: '{category_sel_key}'")

        if not category_opts:
            print("No category options found!")
            return

        # Find Religion & Spirituality
        religion_opt = None
        for o in category_opts:
            if 'religion' in o['t'].lower() or 'spiritual' in o['t'].lower():
                religion_opt = o
                print(f"Found Religion option: {o}")
                break

        if not religion_opt:
            print("Religion not found in options! All options:")
            for o in category_opts:
                print(f"  {o['t']}: {o['v']}")
            return

        # Select Religion & Spirituality
        print(f"\nSelecting: {religion_opt['t']}")
        # The select is identified by react-aui-0 (it's nameless, classname-based)
        sel_locator = page.locator('select.a-native-dropdown').last
        if category_sel_key == 'react-aui-0':
            sel_locator = page.locator('select[name="react-aui-0"]').first

        # Try to select by value
        await page.select_option('select:not([id])', value=religion_opt['v'])
        await page.wait_for_timeout(1500)
        await ss(page, "02_religion_selected")

        # Now look for subcategory select
        all_opts_2 = await page.evaluate("""
            () => {
                const results = {};
                document.querySelectorAll('select').forEach(s => {
                    if (s.offsetParent !== null) {
                        const key = s.id || s.name || ('anon_' + s.className.substring(0, 30));
                        results[key] = Array.from(s.options).map(o => ({v: o.value, t: o.text.trim()}));
                    }
                });
                return results;
            }
        """)

        print("\n=== AFTER RELIGION SELECTION ===")
        for sel_key, opts in all_opts_2.items():
            if '"nodeId"' in str(opts) or '"level"' in str(opts):
                print(f"\nSelect: '{sel_key}' ({len(opts)} options)")
                for o in opts:
                    print(f"  val='{o['v'][:80]}' | '{o['t']}'")

        # Find Christianity
        christianity_opt = None
        for sel_key, opts in all_opts_2.items():
            for o in opts:
                if 'christian' in o['t'].lower():
                    christianity_opt = o
                    print(f"\nFound Christianity: {o}")
                    # Select it
                    try:
                        await page.evaluate(f"""
                            () => {{
                                const selects = Array.from(document.querySelectorAll('select'));
                                const visible = selects.filter(s => s.offsetParent !== null);
                                // Find the one with our value
                                for (const s of visible) {{
                                    const opt = Array.from(s.options).find(o => o.value.includes('level":1'));
                                    if (opt) {{
                                        const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value');
                                        if (nativeSet && nativeSet.set) nativeSet.set.call(s, opt.value.replace('0', ''));
                                    }}
                                }}
                            }}
                        """)
                        # Try select_option
                        await page.select_option(f'select:has(option[value*="level\\":1"])', value=o['v'])
                        await page.wait_for_timeout(1500)
                        break
                    except Exception as e:
                        print(f"  Christianity select error: {e}")
                    break
            if christianity_opt:
                break

        await ss(page, "03_after_subcategory")

        print("\n=== COMPLETE ===")
        print(f"Screenshots: {SCREENSHOTS}")


if __name__ == "__main__":
    asyncio.run(run())

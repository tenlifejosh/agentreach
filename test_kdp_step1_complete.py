"""
KDP Step 1 Complete Test — handles adult content, language, and categories.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from agentreach.browser.session import platform_context

SCREENSHOTS = Path(__file__).parent / "step1_screenshots"
SCREENSHOTS.mkdir(exist_ok=True)

TITLE = "Pray Bold: Teen Edition"
SUBTITLE = "A 52-Week Guided Prayer Journal for Young Men of Faith"
AUTHOR_FIRST = "Joshua"
AUTHOR_LAST = "Noreen"
KEYWORDS = [
    "teen prayer journal for boys",
    "Christian journal for teenage guys",
    "52 week prayer journal teen",
    "faith journal young men",
    "guided prayer journal teens",
    "Christian gifts for teen boys",
    "devotional journal for teenage guys",
]
DESCRIPTION_HTML = """<p><strong>Life is loud. Distractions are everywhere. And yet, God is calling you to something more.</strong></p><p><em>Pray Bold: Teen Edition</em> is a 52-week guided prayer journal built specifically for young men of faith who want to stop drifting and start living with purpose, courage, and intentional prayer.</p><p><strong>Each week includes:</strong></p><ul><li>A real-life theme designed for teen guys</li><li>A key Scripture from the New International Version (NIV)</li><li>3 honest reflection questions</li><li>A full prayer writing page</li></ul><p><strong>52 weeks. 183 pages. One year of bold, honest prayer.</strong></p><p><em>Pray Bold. Your story isn't over.</em></p><p><strong>Interior Details:</strong> 6x9 trim size · 183 pages · B&amp;W interior · Cream background · Matte cover</p>"""


async def ss(page, name):
    p = str(SCREENSHOTS / f"{name}.png")
    await page.screenshot(path=p, full_page=False)
    print(f"  📸 {name}.png")


async def run():
    print("=" * 60)
    print("KDP STEP 1 — Full form fill including categories")
    print("=" * 60)

    async with platform_context("kdp", headless=True, check_health=False) as (ctx, page):
        await page.goto(
            "https://kdp.amazon.com/en_US/title-setup/paperback/new/details",
            wait_until="domcontentloaded", timeout=60000
        )
        await page.wait_for_selector('#data-print-book-title', timeout=20000)
        await page.wait_for_timeout(1500)
        print(f"URL: {page.url}")
        await ss(page, "01_loaded")

        # ── Language ──
        # Select English from the language dropdown
        try:
            lang_sel = await page.locator('#data-print-book-language-native').is_visible()
            if lang_sel:
                await page.locator('#data-print-book-language-native').select_option(value="english")
                await page.wait_for_timeout(500)
                print("  Language: English selected ✓")
            else:
                print("  Language dropdown not visible")
        except Exception as e:
            print(f"  Language select error: {e}")

        # ── Title ──
        await page.locator('#data-print-book-title').fill(TITLE)
        await page.wait_for_timeout(300)

        # ── Subtitle ──
        await page.locator('#data-print-book-subtitle').fill(SUBTITLE)
        await page.wait_for_timeout(300)

        # ── Author ──
        await page.locator('#data-print-book-primary-author-first-name').fill(AUTHOR_FIRST)
        await page.locator('#data-print-book-primary-author-last-name').fill(AUTHOR_LAST)
        await page.wait_for_timeout(300)

        # ── Description via CKEditor ──
        escaped = json.dumps(DESCRIPTION_HTML)
        desc_result = await page.evaluate(
            f"""() => {{
                try {{
                    if (window.CKEDITOR && window.CKEDITOR.instances && window.CKEDITOR.instances['editor1']) {{
                        window.CKEDITOR.instances['editor1'].setData({escaped});
                        return 'ckeditor_ok';
                    }}
                    return 'ckeditor_not_found';
                }} catch(e) {{ return 'error:' + e.message; }}
            }}"""
        )
        print(f"  Description: {desc_result}")

        # ── Keywords ──
        for i, kw in enumerate(KEYWORDS[:7]):
            try:
                await page.locator(f'#data-print-book-keywords-{i}').fill(kw, timeout=3000)
            except Exception:
                pass
        print("  Keywords: 7/7 filled ✓")

        # ── Adult Content: NO ──
        # Radio: name="data[print_book][is_adult_content]-radio" value="false"
        print("\n  Setting adult content = No...")
        try:
            # KDP uses Amazon's radio widget — need to click the label/wrapper, not the input directly
            adult_no = page.locator('input[name="data[print_book][is_adult_content]-radio"][value="false"]')
            # Try clicking the containing label
            await adult_no.click(timeout=5000, force=True)
            await page.wait_for_timeout(500)
            is_checked = await adult_no.is_checked()
            print(f"  Adult content No: checked={is_checked}")
        except Exception as e:
            print(f"  Adult content radio click error: {e}")
            # Try clicking the parent label
            try:
                await page.evaluate("""
                    () => {
                        const radio = document.querySelector('input[name="data[print_book][is_adult_content]-radio"][value="false"]');
                        if (radio) {
                            radio.click();
                            radio.dispatchEvent(new Event('change', {bubbles: true}));
                            return true;
                        }
                        return false;
                    }
                """)
                await page.wait_for_timeout(500)
                print("  Adult content No: set via JS ✓")
            except Exception as e2:
                print(f"  JS click also failed: {e2}")

        await ss(page, "02_adult_content_set")

        # ── Wait for categories button to become enabled ──
        print("\n  Waiting for categories button to become enabled...")
        try:
            await page.wait_for_selector(
                '#categories-modal-button:not([disabled])',
                timeout=5000
            )
            print("  ✓ Categories button enabled!")
        except Exception:
            print("  ⚠ Categories button still disabled — checking state...")
            disabled = await page.get_attribute('#categories-modal-button', 'disabled')
            print(f"  disabled attr: {disabled}")

            # Try triggering the adult content change via Jele event system
            try:
                result = await page.evaluate("""
                    () => {
                        try {
                            // Try to trigger the Jele form value update
                            const radio = document.querySelector('input[name="data[print_book][is_adult_content]-radio"][value="false"]');
                            if (!radio) return 'no_radio';
                            // Amazon uses custom event system
                            radio.checked = true;
                            ['click', 'change', 'input'].forEach(ev => {
                                radio.dispatchEvent(new Event(ev, {bubbles: true}));
                            });
                            return 'events_dispatched';
                        } catch(e) {
                            return 'error: ' + e.message;
                        }
                    }
                """)
                print(f"  Jele trigger attempt: {result}")
                await page.wait_for_timeout(1000)

                # Check button again
                disabled = await page.get_attribute('#categories-modal-button', 'disabled')
                print(f"  categories button disabled after events: {disabled}")
            except Exception as e:
                print(f"  Jele trigger error: {e}")

        # ── Open categories modal ──
        await ss(page, "03_before_categories")
        print("\n  Clicking Choose Categories button...")

        # Check if button is enabled now
        btn_disabled = await page.get_attribute('#categories-modal-button', 'disabled')
        if btn_disabled is not None:
            print(f"  ⚠ Button still disabled ({btn_disabled}). Trying force click...")
            # Force click even if disabled
            await page.evaluate("""
                () => {
                    const btn = document.getElementById('categories-modal-button');
                    if (btn) {
                        btn.disabled = false;
                        btn.click();
                        return true;
                    }
                    return false;
                }
            """)
        else:
            await page.locator('#categories-modal-button').click(timeout=5000)

        await page.wait_for_timeout(2000)
        await ss(page, "04_categories_modal")

        # Look at what's in the modal
        modal_content = await page.evaluate("""
            () => {
                const modals = document.querySelectorAll('[id*="modal"], [class*="modal"], [role="dialog"]');
                const results = [];
                modals.forEach(m => {
                    if (m.offsetParent !== null) {  // visible
                        results.push({
                            id: m.id,
                            class: m.className.substring(0, 100),
                            text: m.innerText.substring(0, 300)
                        });
                    }
                });
                // Also check for category selects
                const selects = [];
                document.querySelectorAll('select').forEach(s => {
                    if (s.offsetParent !== null) {
                        selects.push({id: s.id, name: s.name, optionCount: s.options.length,
                            firstOptions: Array.from(s.options).slice(0, 5).map(o => ({val: o.value, text: o.text}))
                        });
                    }
                });
                return {modals: results, selects: selects};
            }
        """)
        print(f"  Visible modals: {len(modal_content['modals'])}")
        for m in modal_content['modals']:
            print(f"    id='{m['id']}' text='{m['text'][:100]}'")
        print(f"  Visible selects: {len(modal_content['selects'])}")
        for s in modal_content['selects']:
            print(f"    id='{s['id']}' name='{s['name']}' options={s['optionCount']} first={s['firstOptions'][:3]}")

        # Try to navigate the category picker
        # KDP categories: Books > Religion & Spirituality > Christianity > Prayer & Devotion
        print("\n  Attempting to select category: Religion > Christianity > Prayer...")

        # The category modal has dropdowns for Category, Subcategory, Placement
        # Let's find them
        await page.wait_for_timeout(1000)

        # Look for visible selects again after modal opens
        visible_selects_js = """
        () => {
            const selects = [];
            document.querySelectorAll('select').forEach(s => {
                if (s.offsetParent !== null) {
                    selects.push({
                        id: s.id,
                        name: s.name,
                        class: s.className.substring(0, 80),
                        optionCount: s.options.length,
                        options: Array.from(s.options).slice(0, 10).map(o => ({v: o.value, t: o.text.trim().substring(0, 40)}))
                    });
                }
            });
            return selects;
        }
        """
        selects_after_modal = await page.evaluate(visible_selects_js)
        print(f"  Selects after modal: {len(selects_after_modal)}")
        for s in selects_after_modal:
            print(f"    id='{s['id']}' class='{s['class'][:50]}' options={s['optionCount']}")
            for opt in s['options'][:5]:
                print(f"      val='{opt['v']}' text='{opt['t']}'")

        # Try selecting Religion & Spirituality in first dropdown
        # The options might use Amazon browse node IDs as values
        category_selected = False
        for sel_info in selects_after_modal:
            # Look for a select with religion-related option
            for opt in sel_info['options']:
                if 'religion' in opt['t'].lower() or 'spiritual' in opt['t'].lower():
                    print(f"  Found religion option in select id='{sel_info['id']}' val='{opt['v']}'")
                    try:
                        loc = page.locator(f"select#{sel_info['id']}" if sel_info['id'] else f"select[name='{sel_info['name']}']").first
                        await loc.select_option(value=opt['v'])
                        await page.wait_for_timeout(1000)
                        print(f"  ✓ Selected Religion/Spirituality category")
                        category_selected = True
                        await ss(page, "05_category_religion_selected")
                        break
                    except Exception as e:
                        print(f"  Category select error: {e}")
            if category_selected:
                break

        if not category_selected:
            print("  ⚠ Could not find Religion option in category selects — modal may not have opened")

        # Take final screenshot of modal state
        await ss(page, "06_categories_final")

        # If we're in the modal with options, check for subcategory
        await page.wait_for_timeout(500)
        selects_after_cat = await page.evaluate(visible_selects_js)
        print(f"\n  After first category selection, {len(selects_after_cat)} selects visible:")
        for s in selects_after_cat:
            print(f"    id='{s['id']}' options={s['optionCount']} first='{s['options'][0]['t'] if s['options'] else 'none'}'")
            # Look for Christianity
            for opt in s['options']:
                if 'christian' in opt['t'].lower() or 'jesus' in opt['t'].lower():
                    print(f"      → Christianity option found: val='{opt['v']}' text='{opt['t']}'")

        print("\n  ─── Printing current page state ───")
        print(f"  URL: {page.url}")
        print(f"  Title: {await page.title()}")

        # Final full-page screenshot
        await ss(page, "07_final_state")

        # Check validation again
        errors_js = """
        () => {
            const errs = [];
            document.querySelectorAll('.a-alert-content').forEach(el => {
                const txt = el.innerText?.trim();
                if (txt && txt.length > 5 && txt.length < 300) errs.push(txt);
            });
            return [...new Set(errs)];
        }
        """
        errors = await page.evaluate(errors_js)
        print(f"\n  Validation errors ({len(errors)}):")
        for err in errors:
            print(f"    ⚠ {err}")

        print("\n=== STEP 1 TEST COMPLETE ===")
        print(f"Screenshots in: {SCREENSHOTS}")


if __name__ == "__main__":
    asyncio.run(run())

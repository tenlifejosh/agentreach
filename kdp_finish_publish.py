"""
KDP Finish & Publish Script — Pray Bold: Teen Edition
Book ID: 2XPF7965VJP

Steps:
1. Complete details step (Save and Continue via JS click)
2. Complete content step (select interior, upload cover, handle ISBN, Save and Continue)
3. Complete pricing step (set $12.99, click Publish)
4. Verify bookshelf status
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.browser.session import platform_context

BOOK_ID = "2XPF7965VJP"
COVER = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/cover-full-wrap.pdf"

BASE_URL = f"https://kdp.amazon.com/en_US/title-setup/paperback/{BOOK_ID}"
DETAILS_URL = f"https://kdp.amazon.com/action/dualbookshelf.editpaperbackdetails/en_US/title-setup/paperback/{BOOK_ID}/details?ref_=kdp_BS_D_ta_de_main"
CONTENT_URL = f"https://kdp.amazon.com/action/dualbookshelf.editpaperbackcontent/en_US/title-setup/paperback/{BOOK_ID}/content?ref_=kdp_BS_D_ta_co"
PRICING_URL = f"https://kdp.amazon.com/action/dualbookshelf.editpaperbackpricing/en_US/title-setup/paperback/{BOOK_ID}/pricing?ref_=kdp_BS_D_ta_pr"
BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"

SCREENSHOTS_DIR = Path(__file__).parent / "publish_screenshots"


async def dismiss_modals(page):
    """Hide any overlay modals that intercept clicks."""
    await page.evaluate("""
        document.querySelectorAll(
            '.a-popover, .a-modal, [id*="modal"], [class*="modal"], [class*="popover"]'
        ).forEach(el => {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
            el.style.opacity = '0';
            el.style.pointerEvents = 'none';
        });
    """)


async def js_click(page, selector):
    """Click via JS to bypass modal intercepts."""
    result = await page.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.click();
                return 'clicked: ' + (el.textContent || el.id || el.className).substring(0, 80);
            }}
            return 'NOT FOUND: {selector}';
        }})()
    """)
    print(f"    JS click → {result}")
    return result


async def screenshot(page, name):
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    path = str(SCREENSHOTS_DIR / f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    print(f"    📸 {path}")


async def main():
    print("=" * 60)
    print("KDP FINISH & PUBLISH — Pray Bold: Teen Edition")
    print(f"Book ID: {BOOK_ID}")
    print("=" * 60)

    async with platform_context("kdp", headless=False, check_health=False) as (ctx, page):

        # ─────────────────────────────────────────────────────────────
        # WARMUP: Navigate to bookshelf first to establish session
        # ─────────────────────────────────────────────────────────────
        print("\n[WARMUP] Establishing KDP session via bookshelf...")
        await page.goto(BOOKSHELF_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"  Bookshelf URL: {page.url}")
        if "signin" in page.url:
            print("  ⚠ REDIRECTED TO SIGN-IN — session expired!")
            return
        print("  ✓ Session established")

        # ─────────────────────────────────────────────────────────────
        # STEP 1: DETAILS — Save and Continue
        # ─────────────────────────────────────────────────────────────
        print("\n[STEP 1] Completing Details step...")
        print(f"  → Navigating to: {DETAILS_URL}")
        await page.goto(DETAILS_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"  Current URL: {page.url}")
        print(f"  Page title: {await page.title()}")

        if "signin" in page.url or "ap/signin" in page.url:
            print("  ⚠ REDIRECTED TO SIGN-IN — session expired!")
            return

        await dismiss_modals(page)
        await screenshot(page, "01_details_before_save")

        print("  Clicking Save and Continue via JS...")
        await js_click(page, "#save-and-continue-announce")
        await page.wait_for_timeout(8000)
        await screenshot(page, "02_details_after_save")
        print(f"  URL after save: {page.url}")

        # ─────────────────────────────────────────────────────────────
        # STEP 2: CONTENT — Interior, Cover Upload, ISBN, Save & Continue
        # ─────────────────────────────────────────────────────────────
        print("\n[STEP 2] Completing Content step...")
        print(f"  → Navigating to: {CONTENT_URL}")
        await page.goto(CONTENT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"  Current URL: {page.url}")

        await dismiss_modals(page)
        await screenshot(page, "03_content_initial")

        # Select BW_CREAM interior
        print("  Selecting BW_CREAM interior...")
        interior_result = await page.evaluate("""
            (() => {
                const btn = document.querySelector('button[name="BW_CREAM"]') || 
                            document.querySelector('input[value="BW_CREAM"]') ||
                            document.querySelector('[data-value="BW_CREAM"]');
                if (btn) {
                    btn.click();
                    return 'Selected BW_CREAM: ' + btn.tagName;
                }
                // Try to find any interior option buttons
                const allBtns = Array.from(document.querySelectorAll('button, input[type="radio"]'))
                    .filter(el => el.name && el.name.includes('BW') || 
                                  el.value && el.value.includes('BW'));
                return 'BW_CREAM not found, found: ' + allBtns.map(b => b.name || b.value).join(', ');
            })()
        """)
        print(f"  Interior: {interior_result}")

        await page.wait_for_timeout(1000)
        await screenshot(page, "04_content_interior_selected")

        # Upload cover PDF
        print(f"  Uploading cover: {COVER}")
        cover_path = Path(COVER)
        if not cover_path.exists():
            print(f"  ⚠ Cover file NOT FOUND at: {COVER}")
            return

        cover_input_selector = '#data-print-book-publisher-cover-pdf-only-file-upload-AjaxInput'
        try:
            # Make input visible if hidden
            await page.evaluate(f"""
                const inp = document.querySelector('{cover_input_selector}');
                if (inp) {{
                    inp.style.display = 'block';
                    inp.style.visibility = 'visible';
                    inp.style.opacity = '1';
                    inp.removeAttribute('hidden');
                }}
            """)
            await page.locator(cover_input_selector).set_input_files(str(cover_path))
            print("  ✓ Cover file set for upload")
        except Exception as e:
            print(f"  ✗ Cover upload failed: {e}")
            # Try alternate selector
            alt_selectors = [
                'input[id*="cover-pdf"]',
                'input[id*="cover"][type="file"]',
                'input[accept*="pdf"][id*="cover"]',
                'input[type="file"]',
            ]
            for sel in alt_selectors:
                try:
                    count = await page.locator(sel).count()
                    if count > 0:
                        await page.evaluate(f"""
                            const inp = document.querySelector('{sel}');
                            if (inp) {{
                                inp.style.display = 'block';
                                inp.style.visibility = 'visible';
                                inp.removeAttribute('hidden');
                            }}
                        """)
                        await page.locator(sel).first.set_input_files(str(cover_path))
                        print(f"  ✓ Cover uploaded via alternate selector: {sel}")
                        break
                except Exception as e2:
                    print(f"    Tried {sel}: {e2}")

        print("  ⏳ Waiting 90 seconds for cover to process...")
        for i in range(9):
            await page.wait_for_timeout(10000)
            print(f"  ... {(i+1)*10}s elapsed...")
            # Check for any error/success indicators
            content = await page.content()
            if "approved" in content.lower():
                print(f"  ✓ Cover approved at {(i+1)*10}s!")
                break
            if "error" in content.lower() and "cover" in content.lower():
                print(f"  ⚠ Cover error detected at {(i+1)*10}s, checking...")
                await screenshot(page, f"05_cover_error_{(i+1)*10}s")

        await screenshot(page, "05_content_after_cover_upload")

        # Check page state after cover upload
        page_content = await page.content()
        print(f"  Page has 'approved': {'approved' in page_content.lower()}")
        print(f"  Page has 'processing': {'processing' in page_content.lower()}")
        print(f"  Page has 'ISBN': {'ISBN' in page_content}")
        print(f"  Page has 'error': {'error' in page_content.lower()}")

        # Handle ISBN if needed
        isbn_check = await page.evaluate("""
            (() => {
                // Look for ISBN error or assignment option
                const isbnBtn = document.querySelector(
                    'input[id*="free"][id*="isbn"], button[id*="free"][id*="isbn"], ' +
                    'label[for*="free"][for*="isbn"], ' +
                    'input[id*="kdp-isbn"], label[for*="kdp-isbn"], ' +
                    'input[value*="KDP_ASSIGNED"], label[for*="KDP_ASSIGNED"]'
                );
                if (isbnBtn) {
                    isbnBtn.click();
                    return 'ISBN option clicked: ' + (isbnBtn.id || isbnBtn.htmlFor || isbnBtn.value);
                }
                
                // Broader search
                const allElements = Array.from(document.querySelectorAll('input, button, label'))
                    .filter(el => {
                        const text = (el.textContent + el.id + el.value + (el.htmlFor || '')).toLowerCase();
                        return text.includes('isbn') && (text.includes('free') || text.includes('assign') || text.includes('kdp'));
                    });
                if (allElements.length > 0) {
                    allElements[0].click();
                    const el = allElements[0];
                    return 'ISBN element clicked: tag=' + el.tagName + ' id=' + el.id + ' text=' + el.textContent.substring(0, 60);
                }
                return 'No ISBN selector found (may not be needed)';
            })()
        """)
        print(f"  ISBN check: {isbn_check}")
        await page.wait_for_timeout(1000)

        # Save and Continue on Content step
        print("  Clicking Save and Continue on content step...")
        await dismiss_modals(page)
        await js_click(page, "#save-and-continue-announce")
        await page.wait_for_timeout(5000)
        await screenshot(page, "06_content_after_save")
        print(f"  URL after content save: {page.url}")

        # ─────────────────────────────────────────────────────────────
        # STEP 3: PRICING — Set $12.99, Publish
        # ─────────────────────────────────────────────────────────────
        print("\n[STEP 3] Completing Pricing step...")
        print(f"  → Navigating to: {PRICING_URL}")
        await page.goto(PRICING_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"  Current URL: {page.url}")

        await dismiss_modals(page)
        await screenshot(page, "07_pricing_initial")

        # Set price $12.99
        print("  Setting US price to $12.99...")
        price_result = await page.evaluate("""
            (() => {
                // Try the exact selector from task instructions
                let inp = document.querySelector('input[name="data[print_book][amazon_channel][us][price_vat_exclusive]"]');
                
                if (!inp) {
                    // Try alternate selectors
                    inp = document.querySelector('input[name*="us"][name*="price"]') ||
                          document.querySelector('input[id*="us"][id*="price"]') ||
                          document.querySelector('input[placeholder*="9.99"]') ||
                          document.querySelector('input[data-channel="amazon"][data-marketplace="us"]');
                }
                
                if (!inp) {
                    // Find all price inputs
                    const allInputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"]'))
                        .filter(el => {
                            const ctx = (el.name + el.id + el.placeholder + (el.getAttribute('aria-label') || '')).toLowerCase();
                            return ctx.includes('price') || ctx.includes('usd') || ctx.includes('us');
                        });
                    if (allInputs.length > 0) inp = allInputs[0];
                }
                
                if (inp) {
                    inp.focus();
                    inp.select();
                    // Clear and set value
                    inp.value = '';
                    document.execCommand('insertText', false, '12.99');
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    inp.dispatchEvent(new Event('blur', {bubbles: true}));
                    return 'Price set: name=' + inp.name + ' id=' + inp.id + ' value=' + inp.value;
                }
                
                return 'No price input found';
            })()
        """)
        print(f"  Price result: {price_result}")
        await page.wait_for_timeout(1500)
        await screenshot(page, "08_pricing_price_set")

        # Click Publish
        print("  Clicking Publish...")
        await dismiss_modals(page)
        publish_result = await js_click(page, "#save-and-publish-announce")
        print(f"  Publish click: {publish_result}")
        await page.wait_for_timeout(8000)
        await screenshot(page, "09_after_publish_click")
        print(f"  URL after publish: {page.url}")

        # ─────────────────────────────────────────────────────────────
        # STEP 4: VERIFY BOOKSHELF STATUS
        # ─────────────────────────────────────────────────────────────
        print("\n[STEP 4] Checking bookshelf status...")
        await page.goto(BOOKSHELF_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        await screenshot(page, "10_bookshelf_final")

        bookshelf_content = await page.content()
        
        # Check for various statuses
        statuses = {
            "In Review": "in review" in bookshelf_content.lower(),
            "Live": "live" in bookshelf_content.lower(),
            "Under Review": "under review" in bookshelf_content.lower(),
            "In Progress": "in progress" in bookshelf_content.lower(),
            "Pray Bold": "pray bold" in bookshelf_content.lower(),
        }
        
        print("  Bookshelf status indicators:")
        for k, v in statuses.items():
            print(f"    {k}: {v}")

        # Extract relevant text from bookshelf
        status_text = await page.evaluate(f"""
            (() => {{
                const bookEntries = Array.from(document.querySelectorAll(
                    '.book-status, [class*="status"], [id*="status"], ' +
                    '.title-name, [class*="title"]'
                ));
                const texts = bookEntries
                    .map(el => el.textContent.trim())
                    .filter(t => t.length > 0 && t.length < 200);
                return texts.slice(0, 20).join(' | ');
            }})()
        """)
        print(f"  Status text from page: {status_text[:500] if status_text else 'none'}")

        print("\n" + "=" * 60)
        if statuses["In Review"] or statuses["Under Review"]:
            print("✅ SUCCESS — Book is IN REVIEW!")
        elif statuses["Live"]:
            print("✅ SUCCESS — Book is LIVE!")
        elif statuses["In Progress"]:
            print("⚠ Book still In Progress — publish may need manual intervention")
        else:
            print("⚠ Status unclear — check screenshots")
        print("=" * 60)

        print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

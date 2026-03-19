"""
Full KDP upload test for Pray Bold: Teen Edition
Tests the fixed driver step by step with screenshots.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.browser.session import platform_context
from agentreach.browser.uploader import upload_file, wait_for_upload_complete

MANUSCRIPT = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/interior.pdf")
COVER = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/cover-full-wrap.pdf")

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
DESCRIPTION_HTML = """<p><strong>Life is loud. Distractions are everywhere. And yet, God is calling you to something more.</strong></p>

<p><em>Pray Bold: Teen Edition</em> is a 52-week guided prayer journal built specifically for young men of faith who want to stop drifting and start living with purpose, courage, and intentional prayer.</p>

<p>This isn't a devotional you read once and forget. It's a year-long conversation — between you and the God who made you, knows you, and has a powerful plan for your life.</p>

<p><strong>Each week includes:</strong></p>
<ul>
<li>A real-life theme designed for teen guys (identity, peer pressure, social media, courage, purpose, mental health, family, faith under fire, and more)</li>
<li>A key Scripture from the New International Version (NIV)</li>
<li>3 honest reflection questions that go beyond the surface</li>
<li>A full prayer writing page with lined space to write your prayers by hand</li>
</ul>

<p><strong>Also includes:</strong></p>
<ul>
<li>12 Monthly Reflection pages to review each month's themes</li>
<li>Year in Review section to celebrate your growth</li>
<li>Notes pages for extra thoughts, Scriptures, and prayers</li>
</ul>

<p><strong>52 weeks. 183 pages. One year of bold, honest prayer.</strong></p>

<p>Whether you're new to prayer or you've been walking with God for years, this journal will challenge you, grow you, and keep you coming back. It makes an excellent gift for confirmation, graduation, Christmas, or any young man stepping into his faith.</p>

<p><em>Pray Bold. Your story isn't over.</em></p>

<p><strong>Interior Details:</strong> 6x9 trim size · 183 pages · B&amp;W interior · Cream background · Matte cover</p>

<p><em>Scripture quotations are from the Holy Bible, New International Version® (NIV®), Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.™ Used by permission.</em></p>"""

SCREENSHOTS = Path(__file__).parent / "upload_screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


async def screenshot(page, name: str):
    path = str(SCREENSHOTS / f"{name}.png")
    await page.screenshot(path=path, full_page=False)  # viewport only, faster
    print(f"  📸 {name}.png")
    return path


async def run_upload():
    print("=" * 60)
    print("KDP UPLOAD TEST — Pray Bold: Teen Edition")
    print("=" * 60)

    # Verify files exist
    for f in [MANUSCRIPT, COVER]:
        if not f.exists():
            print(f"❌ File not found: {f}")
            sys.exit(1)
        print(f"✓ File exists: {f.name} ({f.stat().st_size // 1024}KB)")

    async with platform_context("kdp", headless=True, check_health=False) as (ctx, page):

        # ════════════════════════════════════════════════
        # STEP 1: Book Details
        # ════════════════════════════════════════════════
        print("\n── STEP 1: Book Details ──")
        await page.goto(
            "https://kdp.amazon.com/en_US/title-setup/paperback/new/details",
            wait_until="domcontentloaded",
            timeout=60000
        )
        await page.wait_for_timeout(2000)
        print(f"  URL: {page.url}")

        if "signin" in page.url:
            print("❌ REDIRECTED TO SIGN-IN — session expired!")
            return

        await page.wait_for_selector('#data-print-book-title', timeout=15000)
        await screenshot(page, "step1_01_loaded")

        # Fill Title
        await page.locator('#data-print-book-title').fill(TITLE)
        await page.wait_for_timeout(300)
        title_val = await page.locator('#data-print-book-title').input_value()
        print(f"  Title: '{title_val}' — {'✓' if title_val == TITLE else '❌'}")

        # Fill Subtitle
        await page.locator('#data-print-book-subtitle').fill(SUBTITLE)
        await page.wait_for_timeout(300)
        subtitle_val = await page.locator('#data-print-book-subtitle').input_value()
        print(f"  Subtitle: '{subtitle_val[:50]}...' — {'✓' if subtitle_val else '❌'}")

        # Fill Author
        await page.locator('#data-print-book-primary-author-first-name').fill(AUTHOR_FIRST)
        await page.locator('#data-print-book-primary-author-last-name').fill(AUTHOR_LAST)
        first_val = await page.locator('#data-print-book-primary-author-first-name').input_value()
        last_val = await page.locator('#data-print-book-primary-author-last-name').input_value()
        print(f"  Author: '{first_val} {last_val}' — {'✓' if first_val and last_val else '❌'}")

        # Fill Description via CKEditor
        import json
        escaped = json.dumps(DESCRIPTION_HTML)
        desc_result = await page.evaluate(
            f"""
            () => {{
                try {{
                    if (window.CKEDITOR && window.CKEDITOR.instances && window.CKEDITOR.instances['editor1']) {{
                        window.CKEDITOR.instances['editor1'].setData({escaped});
                        return 'ckeditor_ok';
                    }}
                    return 'ckeditor_not_found';
                }} catch(e) {{
                    return 'ckeditor_error:' + e.message;
                }}
            }}
            """
        )
        print(f"  Description (CKEditor): {desc_result}")
        await page.wait_for_timeout(500)

        # Fill Keywords
        kw_ok = 0
        for i, kw in enumerate(KEYWORDS[:7]):
            try:
                await page.locator(f'#data-print-book-keywords-{i}').fill(kw, timeout=3000)
                kw_ok += 1
            except Exception as e:
                print(f"  Keyword {i} error: {e}")
        print(f"  Keywords: {kw_ok}/7 filled")

        await screenshot(page, "step1_02_filled")

        # Select "Not adult content" radio (non-adult, should be default)
        # And make sure "non-public-domain" is selected
        try:
            await page.locator('#non-public-domain').check()
        except Exception:
            pass

        # Click Save and Continue
        print("\n  Clicking Save and Continue...")
        try:
            await page.locator('#save-and-continue').click(timeout=10000)
            print("  ✓ Clicked #save-and-continue")
        except Exception as e:
            print(f"  ❌ #save-and-continue click failed: {e}")
            # Try announce version
            try:
                await page.locator('#save-and-continue-announce').click(timeout=5000)
                print("  ✓ Clicked #save-and-continue-announce")
            except Exception as e2:
                print(f"  ❌ Both save buttons failed: {e2}")
                await screenshot(page, "step1_03_save_error")
                return

        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await screenshot(page, "step2_01_loaded")
        print(f"\n── STEP 2: Book Content ──")
        print(f"  URL: {page.url}")

        # Check if we made it to step 2
        if "details" in page.url and "content" not in page.url:
            print("  ⚠ Still on details page — possible validation error")
            # Check for validation errors
            errors_js = """
            () => {
                const errs = [];
                document.querySelectorAll('.a-alert-content, .a-color-error, [class*="error"], [class*="alert"]').forEach(el => {
                    const txt = el.innerText?.trim();
                    if (txt && txt.length < 300) errs.push(txt);
                });
                return [...new Set(errs)].slice(0, 10);
            }
            """
            errors = await page.evaluate(errors_js)
            for err in errors:
                print(f"  VALIDATION: {err}")
            await screenshot(page, "step1_validation_errors")

        # ════════════════════════════════════════════════
        # STEP 2: Book Content (File Uploads)
        # ════════════════════════════════════════════════

        # Wait for content form to load
        await page.wait_for_timeout(2000)

        # Look for manuscript upload elements
        print("\n  Scanning for upload triggers...")
        upload_els_js = """
        () => {
            const els = [];
            document.querySelectorAll('button, a, [role="button"], input[type="file"]').forEach(el => {
                const txt = (el.innerText || el.value || el.id || el.name || '').toLowerCase();
                const id = (el.id || '').toLowerCase();
                const cls = (el.className || '').toLowerCase();
                if (txt.includes('upload') || txt.includes('manuscript') || txt.includes('cover') ||
                    id.includes('upload') || cls.includes('upload') || el.type === 'file') {
                    els.push({
                        tag: el.tagName, id: el.id, type: el.type || '',
                        text: (el.innerText || '').substring(0, 60).trim(),
                        class: (el.className || '').substring(0, 80),
                        visible: el.offsetParent !== null
                    });
                }
            });
            return els;
        }
        """
        upload_els = await page.evaluate(upload_els_js)
        print(f"  Found {len(upload_els)} upload-related elements:")
        for el in upload_els:
            print(f"    [{el['tag']}] id='{el['id']}' type='{el['type']}' text='{el['text']}' vis={el['visible']}")

        # Try manuscript upload
        print("\n  Uploading manuscript PDF...")
        ms_uploaded = await upload_file(
            page, MANUSCRIPT,
            trigger_selector='[id*="upload-manuscript"], button:has-text("Upload"), label:has-text("manuscript")',
            input_selector='input[type="file"]',
        )
        if ms_uploaded:
            print("  ✓ Manuscript upload initiated")
            await wait_for_upload_complete(page, timeout=120000)
            await screenshot(page, "step2_02_manuscript_uploaded")
            print("  ✓ Manuscript upload complete")
        else:
            print("  ❌ Manuscript upload failed — trying direct file input...")
            # Try finding any visible file input
            file_inputs = await page.query_selector_all('input[type="file"]')
            print(f"  Found {len(file_inputs)} file inputs")
            if file_inputs:
                try:
                    await file_inputs[0].set_input_files(str(MANUSCRIPT))
                    await page.wait_for_timeout(2000)
                    print("  ✓ Direct setInputFiles worked for manuscript")
                except Exception as e:
                    print(f"  ❌ Direct setInputFiles also failed: {e}")

        await screenshot(page, "step2_03_after_manuscript")

        print("\n  Uploading cover PDF...")
        cov_uploaded = await upload_file(
            page, COVER,
            trigger_selector='[id*="upload-cover"], button:has-text("cover"), label:has-text("cover")',
            input_selector='input[type="file"]',
        )
        if cov_uploaded:
            print("  ✓ Cover upload initiated")
            await wait_for_upload_complete(page, timeout=120000)
            await screenshot(page, "step2_04_cover_uploaded")
            print("  ✓ Cover upload complete")
        else:
            print("  ❌ Cover upload failed")

        await screenshot(page, "step2_05_after_cover")
        print(f"\n  Current URL: {page.url}")
        print("\n  ℹ️  Stopping here — NOT clicking Save and Continue on Step 2 to avoid creating a duplicate draft.")
        print("  (Step 1 data was saved, Step 2 uploads were attempted)")
        print("\n══════════════════════════════════════")
        print("UPLOAD TEST COMPLETE — review screenshots in upload_screenshots/")
        print("══════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(run_upload())

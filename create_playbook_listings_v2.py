"""
Create two Gumroad product listings v2:
1. The Social Media Agent Master Playbook — $27
2. Reddit Master — The Complete AI Agent Playbook — $17

Fixed flow based on actual Gumroad UI inspection.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/playbook_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

SOCIAL_PDF = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/social-playbook/social-media-agent-playbook.pdf"
REDDIT_PDF = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/reddit-playbook/reddit-master-playbook.pdf"

PRODUCTS = [
    {
        "name": "The Social Media Agent Master Playbook — 2026 Edition",
        "price": "27",
        "description": """The most comprehensive AI social media operations manual ever written.

1,469 lines covering every major platform:
• X/Twitter — algorithm weights, content strategy, warm-up protocol, hooks
• Instagram — Reels strategy, SEO, 30-minute engagement window
• TikTok — 2026 algorithm, rewatch rate optimization, follower-first model
• Reddit — 90-day warm-up, subreddit field guides, promotion without bans
• Pinterest — SEO-first strategy, pin formats, evergreen growth
• Facebook Organic + Facebook Ads (Advantage+, creative, bidding)
• Google Ads — PMax strategy, asset requirements, bidding progression
• Nextdoor — hyperlocal marketing, recommendation strategy

Also includes:
✓ Hook library with 40+ proven formulas by platform
✓ Content velocity targets for every platform
✓ Weekly/daily operations checklist
✓ Account warm-up protocols
✓ Trust ladder and conversion architecture
✓ Analytics and optimization loops
✓ Emergency playbooks for algorithm changes, negative viral moments, ad suspensions

Built for AI agents and human marketers. Every section is actionable, research-backed, and specific.

This is what we built to power our own autonomous social media agent. Now it's yours.""",
        "file": SOCIAL_PDF,
        "slug": "social-media-agent-playbook",
    },
    {
        "name": "Reddit Master — The Complete AI Agent Playbook",
        "price": "17",
        "description": """Stop getting banned. Start getting results.

Reddit is the most powerful — and most unforgiving — platform for organic traffic in 2026. Reddit content appears in 97.5% of product review queries on Google. AI systems like ChatGPT and Claude cite Reddit constantly.

This 734-line playbook covers everything:

• How Reddit's algorithm actually works
• The 90-day account warm-up protocol (week by week)
• Subreddit field guides for r/personalfinance, r/Christianity, r/Anxiety, r/Entrepreneur, r/Parenting, r/povertyfinance, r/selfimprovement, r/budgeting
• Comment mastery — structure, length, tone, how to get upvoted
• The promotion playbook — how to eventually mention products without getting banned
• Daily Reddit routine
• Red flags that mean you're about to get banned
• Recovery protocol when posts get removed

This is the exact playbook we built to run u/HutchCOO autonomously. Zero bans. Genuine community growth.

If you're using AI agents to grow on Reddit, this is the manual.""",
        "file": REDDIT_PDF,
        "slug": "reddit-master-playbook",
    },
]


async def ss(page: Page, name: str):
    await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
    print(f"  📸 {name}")


async def dump_page(page: Page, prefix=""):
    """Dump visible buttons and key text for debugging."""
    body = await page.locator("body").inner_text()
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    print(f"{prefix}Page text (first 30 lines):")
    for line in lines[:30]:
        print(f"{prefix}  {line}")

    btns = page.locator("button")
    count = await btns.count()
    visible_btns = []
    for i in range(min(count, 30)):
        try:
            t = await btns.nth(i).inner_text()
            v = await btns.nth(i).is_visible()
            if v and t.strip():
                visible_btns.append(t.strip())
        except:
            pass
    if visible_btns:
        print(f"{prefix}Visible buttons: {visible_btns}")


async def create_product(page: Page, product: dict) -> dict:
    name = product["name"]
    price = product["price"]
    description = product["description"]
    file_path = product["file"]
    slug = product["slug"]
    result = {"name": name, "success": False, "product_id": None, "url": None}

    print(f"\n{'='*60}")
    print(f"Creating: {name}")
    print(f"{'='*60}")

    # Step 1: Open new product form
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_01_new.png")

    # Fill product name
    name_input = page.locator('input[placeholder="Name of product"]').first
    await name_input.wait_for(state="visible", timeout=15000)
    await name_input.fill(name)
    await page.wait_for_timeout(300)
    print(f"  ✓ Name filled")

    # Fill price (click and clear first, then type)
    price_input = page.locator('input[name="price"], input[placeholder*="rice"]').first
    try:
        await price_input.wait_for(state="visible", timeout=5000)
        await price_input.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await price_input.type(price)
        await page.wait_for_timeout(300)
        print(f"  ✓ Price filled: ${price}")
    except Exception as e:
        print(f"  Price input not visible yet: {e}")

    # Make sure "Digital product" type is selected (default)
    # Click "Next: Customize" or "Next"
    next_btn = page.locator('button:has-text("Next")').first
    await next_btn.wait_for(state="visible", timeout=10000)
    print("  Clicking Next...")
    await next_btn.click()
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_02_after_next.png")

    # Check if price is now visible (2nd step of modal might show price)
    try:
        price_input2 = page.locator('input[name="price"], input[placeholder*="rice"]').first
        if await price_input2.is_visible():
            await price_input2.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Backspace")
            await price_input2.type(price)
            await page.wait_for_timeout(300)
            print(f"  ✓ Price filled on step 2: ${price}")
    except:
        pass

    # Click "Customize" / Next / Create
    for btn_text in ["Customize", "Create product", "Next: Customize", "Next"]:
        btn = page.locator(f'button:has-text("{btn_text}")').first
        if await btn.count() > 0 and await btn.is_visible():
            print(f"  Clicking '{btn_text}'...")
            await btn.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            break

    print(f"  URL: {page.url}")
    await ss(page, f"{slug}_03_after_create.png")

    # Extract product ID
    url = page.url
    product_id = None
    if "/products/" in url:
        pid = url.split("/products/")[1].split("/")[0].split("?")[0]
        if pid != "new":
            product_id = pid
            result["product_id"] = product_id
            print(f"  ✓ Product ID: {product_id}")
        else:
            # Still on /products/new — dump page for debugging
            await dump_page(page, "  ")

    if not product_id:
        print("  ✗ Could not get product ID, aborting this product")
        return result

    # Step 2: Fill description on edit page
    print("Step 2: Fill description...")
    edit_url = f"https://gumroad.com/products/{product_id}/edit"
    await page.goto(edit_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    try:
        desc_editor = page.locator('[contenteditable="true"]').first
        await desc_editor.wait_for(state="visible", timeout=10000)
        await desc_editor.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.type(description, delay=1)
        await page.wait_for_timeout(500)
        print("  ✓ Description filled")
    except Exception as e:
        print(f"  Description: {e}")

    # Save Product tab
    await ss(page, f"{slug}_04_before_save.png")
    save_btn = page.locator('button:has-text("Save and continue")').first
    try:
        await save_btn.wait_for(state="visible", timeout=8000)
        await save_btn.click()
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(2000)
        print(f"  ✓ Saved. URL: {page.url}")
    except Exception as e:
        print(f"  Save: {e}")

    await ss(page, f"{slug}_05_after_save.png")

    # Step 3: Upload file on Content tab
    print("Step 3: Upload file...")
    content_url = f"https://gumroad.com/products/{product_id}/edit/content"
    await page.goto(content_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_06_content.png")

    file_uploaded = False
    try:
        # Check for file input
        fi = page.locator('input[type="file"]')
        fi_count = await fi.count()

        if fi_count > 0:
            print(f"  Direct file input found ({fi_count}), uploading...")
            await fi.first.set_input_files(file_path)
            print("  Waiting for upload to complete...")
            # Wait up to 3 min
            for i in range(36):
                await page.wait_for_timeout(5000)
                body_txt = await page.locator("body").inner_text()
                pdf_name = Path(file_path).name
                if pdf_name in body_txt or "100%" in body_txt:
                    print(f"  ✓ Upload complete")
                    file_uploaded = True
                    break
                if "error" in body_txt.lower() and i > 3:
                    print(f"  Upload error detected")
                    break
                if i % 3 == 2:
                    print(f"  Still uploading... ({(i+1)*5}s)")
        else:
            # Try clicking upload button and using file chooser
            upload_btn = page.locator('button:has-text("Upload")').first
            if await upload_btn.count() > 0:
                print("  Using file chooser via Upload button...")
                try:
                    async with page.expect_file_chooser(timeout=8000) as fc_info:
                        await upload_btn.click()
                    fc = await fc_info.value
                    await fc.set_files(file_path)
                    await page.wait_for_timeout(15000)
                    print("  File set")
                    file_uploaded = True
                except Exception as e2:
                    print(f"  File chooser: {e2}")
            else:
                print("  No upload mechanism found")
                await dump_page(page, "  ")

    except Exception as e:
        print(f"  Upload error: {e}")

    await ss(page, f"{slug}_07_after_upload.png")

    # Save Content tab
    try:
        save_c = page.locator('button:has-text("Save and continue")').first
        if await save_c.count() > 0 and await save_c.is_visible():
            await save_c.click()
            await page.wait_for_timeout(3000)
            print("  ✓ Content tab saved")
    except:
        pass

    # Step 4: Publish — step through wizard
    print("Step 4: Publishing...")
    for attempt in range(8):
        cur_url = page.url
        body = await page.locator("body").inner_text()

        if "Unpublish" in body:
            print(f"  ✓ PUBLISHED!")
            result["success"] = True
            break

        pub_btn = page.locator('button:has-text("Publish")').first
        if await pub_btn.count() > 0 and await pub_btn.is_visible():
            print(f"  Clicking Publish (attempt {attempt+1})...")
            await pub_btn.click()
            await page.wait_for_timeout(5000)
            await ss(page, f"{slug}_08_after_publish.png")
            body2 = await page.locator("body").inner_text()
            if "Unpublish" in body2:
                print(f"  ✓ PUBLISHED SUCCESSFULLY!")
                result["success"] = True
            break

        # Advance through wizard
        save_btn = page.locator('button:has-text("Save and continue")').first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            print(f"  Save and continue (step {attempt+1})...")
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
        else:
            # Navigate manually
            if "/content" not in cur_url and "/receipt" not in cur_url and "/share" not in cur_url and f"/edit" == cur_url.split(product_id)[-1]:
                next_section = f"https://gumroad.com/products/{product_id}/edit/content"
            elif "/content" in cur_url:
                next_section = f"https://gumroad.com/products/{product_id}/edit/receipt"
            elif "/receipt" in cur_url:
                next_section = f"https://gumroad.com/products/{product_id}/edit/share"
            elif "/share" in cur_url:
                next_section = f"https://gumroad.com/products/{product_id}/edit"
            else:
                print(f"  No wizard navigation found at {cur_url}")
                await dump_page(page, "  ")
                break
            print(f"  Navigating to: {next_section}")
            await page.goto(next_section, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)

    # Final screenshot
    await ss(page, f"{slug}_09_final.png")

    if result["success"] and product_id:
        result["url"] = f"https://app.gumroad.com/products/{product_id}"

    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Gumroad Product Creator v2")

        # Verify login
        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "sign" in page.url:
            print("❌ Not logged in!")
            return
        print(f"✓ Logged in at: {page.url}")

        for product in PRODUCTS:
            r = await create_product(page, product)
            results.append(r)

    # Report
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    for r in results:
        s = "✅" if r["success"] else "❌"
        print(f"\n{s} {r['name']}")
        if r.get("product_id"):
            print(f"  ID: {r['product_id']}")
            print(f"  Edit: https://gumroad.com/products/{r['product_id']}/edit")
        if r.get("url"):
            print(f"  Dashboard: {r['url']}")

    # Save
    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/playbook_results.txt")
    with open(results_path, "w") as f:
        for r in results:
            f.write(f"Product: {r['name']}\n")
            f.write(f"Success: {r['success']}\n")
            f.write(f"Product ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit URL: https://gumroad.com/products/{r['product_id']}/edit\n")
            f.write("-"*40 + "\n")
    print(f"\nResults: {results_path}")


asyncio.run(main())

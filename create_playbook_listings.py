"""
Create two Gumroad product listings:
1. The Social Media Agent Master Playbook — $27
2. Reddit Master — The Complete AI Agent Playbook — $17

Full flow: create product → fill details → upload PDF → publish
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

SOCIAL_PRODUCT = {
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
}

REDDIT_PRODUCT = {
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
}


async def screenshot(page: Page, name: str):
    p = SCREENSHOTS_DIR / name
    await page.screenshot(path=str(p), full_page=True)
    print(f"  📸 {name}")


async def create_and_publish(page: Page, product: dict) -> dict:
    """Create a product, upload file, and publish. Returns result dict."""
    name = product["name"]
    price = product["price"]
    description = product["description"]
    file_path = product["file"]
    slug = product["slug"]

    result = {"name": name, "success": False, "url": None, "product_id": None, "error": None}

    print(f"\n{'='*60}")
    print(f"Creating: {name}")
    print(f"{'='*60}")

    # Step 1: Navigate to new product page
    print("Step 1: Navigate to new product page...")
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)
    await screenshot(page, f"{slug}_01_new.png")

    # Fill product name
    try:
        name_input = page.locator('input[placeholder*="Name"], input[placeholder*="name"], input[name="name"]').first
        await name_input.wait_for(timeout=10000)
        await name_input.click()
        await name_input.fill(name)
        await page.wait_for_timeout(500)
        print(f"  ✓ Name filled: {name[:50]}...")
    except Exception as e:
        print(f"  ✗ Name input: {e}")
        # Try any visible text input
        inputs = page.locator('input[type="text"]')
        count = await inputs.count()
        print(f"  Found {count} text inputs")
        if count > 0:
            await inputs.first.fill(name)

    # Fill price
    try:
        price_input = page.locator('input[placeholder*="rice"], input[name="price"], input[placeholder*="$"]').first
        await price_input.wait_for(timeout=5000)
        await price_input.click()
        await price_input.triple_click()
        await price_input.fill(price)
        await page.wait_for_timeout(300)
        print(f"  ✓ Price filled: ${price}")
    except Exception as e:
        print(f"  ✗ Price input: {e}")

    # Click Next/Create
    try:
        next_btn = page.locator('button:has-text("Next"), button:has-text("Create product"), button[type="submit"]').first
        await next_btn.wait_for(timeout=5000)
        print("  Clicking Next/Create...")
        await next_btn.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"  URL after create: {page.url}")
    except Exception as e:
        print(f"  ✗ Next button: {e}")

    await screenshot(page, f"{slug}_02_after_create.png")

    # Get product ID from URL
    current_url = page.url
    product_id = None
    if "/products/" in current_url:
        product_id = current_url.split("/products/")[1].split("/")[0].split("?")[0]
        result["product_id"] = product_id
        print(f"  Product ID: {product_id}")

    # Step 2: Fill description
    print("Step 2: Fill description...")
    try:
        # Gumroad uses contenteditable div for description
        desc_editor = page.locator('[contenteditable="true"]').first
        await desc_editor.wait_for(timeout=8000)
        await desc_editor.click()
        await page.keyboard.press("Control+a")
        await desc_editor.type(description, delay=2)
        await page.wait_for_timeout(1000)
        print("  ✓ Description filled")
    except Exception as e:
        print(f"  ✗ Description: {e}")
        # Try textarea
        try:
            textarea = page.locator('textarea[name="description"], textarea[placeholder*="escription"]').first
            await textarea.wait_for(timeout=3000)
            await textarea.fill(description)
            print("  ✓ Description via textarea")
        except Exception as e2:
            print(f"  ✗ Textarea also failed: {e2}")

    # Save and continue from Product tab
    print("Step 3: Save and continue (Product tab)...")
    try:
        save_btn = page.locator('button:has-text("Save and continue"), button:has-text("Save changes")').first
        await save_btn.wait_for(timeout=5000)
        await save_btn.click()
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(3000)
        print(f"  URL: {page.url}")
    except Exception as e:
        print(f"  ✗ Save: {e}")

    await screenshot(page, f"{slug}_03_after_save.png")

    # Step 4: Upload file (Content tab)
    print("Step 4: Navigate to Content tab for file upload...")
    if product_id:
        content_url = f"https://gumroad.com/products/{product_id}/edit/content"
        await page.goto(content_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await screenshot(page, f"{slug}_04_content.png")

        print("  Attempting file upload...")
        try:
            # Try file chooser via Upload button click
            upload_trigger = page.locator(
                'button:has-text("Upload files"), button:has-text("Upload your files"), '
                'button:has-text("Upload"), [class*="upload"] button'
            ).first

            fi_count = await page.locator('input[type="file"]').count()
            print(f"  File inputs found: {fi_count}")

            if fi_count > 0:
                # Direct input
                await page.locator('input[type="file"]').first.set_input_files(file_path)
                print("  File set via direct input")
                # Wait for upload
                await page.wait_for_timeout(3000)
                for attempt in range(24):  # up to 2 min
                    body_text = await page.locator("body").inner_text()
                    pdf_name = Path(file_path).name
                    if pdf_name in body_text or "100%" in body_text or "complete" in body_text.lower():
                        print(f"  ✓ Upload complete (attempt {attempt+1})")
                        break
                    if attempt % 6 == 5:
                        print(f"  Waiting for upload... ({(attempt+1)*5}s)")
                    await page.wait_for_timeout(5000)
            else:
                # Try file chooser
                try:
                    async with page.expect_file_chooser(timeout=8000) as fc_info:
                        await upload_trigger.click()
                    fc = await fc_info.value
                    await fc.set_files(file_path)
                    print("  File set via file chooser")
                    await page.wait_for_timeout(15000)
                except Exception as e3:
                    print(f"  File chooser failed: {e3}")

            await screenshot(page, f"{slug}_05_after_upload.png")
        except Exception as e:
            print(f"  ✗ Upload error: {e}")

        # Save content
        try:
            save_content = page.locator('button:has-text("Save and continue"), button:has-text("Save changes")').first
            if await save_content.count() > 0:
                await save_content.click()
                await page.wait_for_timeout(3000)
                print("  ✓ Content saved")
        except Exception as e:
            print(f"  Content save: {e}")

    # Step 5: Publish
    print("Step 5: Publishing product...")
    if product_id:
        edit_url = f"https://gumroad.com/products/{product_id}/edit"

        # Try stepping through wizard tabs to reach Publish button
        for attempt in range(6):
            await screenshot(page, f"{slug}_06_{attempt}_wizard.png")
            body = await page.locator("body").inner_text()

            # Check if already published
            if "Unpublish" in body:
                print(f"  ✓ Product is PUBLISHED!")
                result["success"] = True
                break

            # Look for Publish button
            pub_btn = page.locator('button:has-text("Publish")').first
            pub_count = await pub_btn.count()
            pub_visible = await pub_btn.is_visible() if pub_count > 0 else False

            if pub_count > 0 and pub_visible:
                print(f"  Found Publish button (attempt {attempt+1}), clicking...")
                await pub_btn.click()
                await page.wait_for_timeout(4000)
                await screenshot(page, f"{slug}_07_after_publish.png")

                # Verify
                body2 = await page.locator("body").inner_text()
                if "Unpublish" in body2:
                    print("  ✓ PUBLISHED SUCCESSFULLY!")
                    result["success"] = True
                break

            # Try Save and continue to advance
            save_btn = page.locator('button:has-text("Save and continue")').first
            if await save_btn.count() > 0 and await save_btn.is_visible():
                print(f"  Clicking 'Save and continue' (attempt {attempt+1})...")
                await save_btn.click()
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_timeout(2000)
                print(f"  URL: {page.url}")
            else:
                # Navigate to next section manually
                # Check current URL to determine where we are
                cur = page.url
                if "content" not in cur and "receipt" not in cur and "share" not in cur:
                    await page.goto(f"{edit_url}/content", wait_until="networkidle", timeout=20000)
                elif "content" in cur:
                    await page.goto(f"{edit_url}/receipt", wait_until="networkidle", timeout=20000)
                elif "receipt" in cur:
                    await page.goto(f"{edit_url}/share", wait_until="networkidle", timeout=20000)
                elif "share" in cur:
                    await page.goto(edit_url, wait_until="networkidle", timeout=20000)
                else:
                    print(f"  No navigation found at attempt {attempt+1}")
                    break
                await page.wait_for_timeout(2000)

    # Build product URL
    if result["success"] and product_id:
        result["url"] = f"https://app.gumroad.com/products/{product_id}"
        # Also try custom URL
        result["gumroad_url"] = f"https://tenlifejosh.gumroad.com/l/{slug}"

    return result


async def main():
    vault = SessionVault()

    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Starting Gumroad product creation...")

        # Verify session
        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "sign_in" in page.url:
            print("❌ Not logged in! Need to harvest Gumroad session first.")
            print("Run: agentreach harvest gumroad")
            return

        print(f"✓ Logged in. URL: {page.url}")
        await screenshot(page, "00_dashboard.png")

        # Create Social Media Playbook
        r1 = await create_and_publish(page, SOCIAL_PRODUCT)
        results.append(r1)

        # Create Reddit Playbook
        r2 = await create_and_publish(page, REDDIT_PRODUCT)
        results.append(r2)

    # Final report
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    for r in results:
        status = "✅ PUBLISHED" if r["success"] else "❌ FAILED"
        print(f"\n{status}: {r['name']}")
        if r.get("product_id"):
            print(f"  Product ID: {r['product_id']}")
        if r.get("url"):
            print(f"  Manage URL: {r['url']}")
        if r.get("gumroad_url"):
            print(f"  Public URL: {r['gumroad_url']}")
        if r.get("error"):
            print(f"  Error: {r['error']}")

    # Save results to file
    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/playbook_results.txt")
    with open(results_path, "w") as f:
        for r in results:
            f.write(f"Product: {r['name']}\n")
            f.write(f"Success: {r['success']}\n")
            f.write(f"Product ID: {r.get('product_id', 'N/A')}\n")
            f.write(f"URL: {r.get('url', 'N/A')}\n")
            f.write(f"Public URL: {r.get('gumroad_url', 'N/A')}\n")
            f.write("-"*40 + "\n")
    print(f"\nResults saved to: {results_path}")


asyncio.run(main())

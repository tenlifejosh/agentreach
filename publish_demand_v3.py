"""
Publish 3 Demand Products to Gumroad (v3 — select product type first)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/demand_v3_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

BASE = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products")

PRODUCTS = [
    {
        "name": "Church AI Toolkit — 50 Bible-Based Prompts + Ministry Templates",
        "price": "37",
        "description": """You've probably already used AI. Maybe you asked it to help with a sermon illustration, or draft a newsletter you didn't have time to write. But if you're like most church leaders, you're doing it without a system.

This toolkit gives you the framework.

The Church AI Toolkit is a complete guide for pastors, ministry directors, church staff, and volunteer leaders who want to use AI as a ministry tool — without compromising authenticity, theological integrity, or the irreplaceable work of the Holy Spirit.

What's included:

THE CHURCH AI TOOLKIT GUIDE (PDF, 20+ pages) — Step-by-step guidance for using AI across every area of church ministry: sermon prep, communications, small group curriculum, pastoral care, admin, and creating your church AI policy.

50 BIBLE-BASED AI PROMPTS — 50 ready-to-use prompts organized by ministry area. Sermon prep, social media, communications, small groups, pastoral care. Copy, fill in the details, get results.

CHURCH AI POLICY TEMPLATE — A complete, customizable AI policy for your church covering permitted uses, prohibited uses, privacy protection, theological review standards, and team accountability.

Who this is for: Pastors who want to use AI without losing their voice. Church administrators drowning in communications. Ministry leaders who want to prepare better curriculum.

The printing press didn't replace the preacher. The microphone didn't replace the anointing. AI won't either — if you use it with wisdom.

Instant download. Three documents included.""",
        "file": str(BASE / "church-ai-toolkit/church-ai-toolkit-bundle.zip"),
        "slug": "church-ai-toolkit",
    },
    {
        "name": "AI Agent Starter Kit — The Non-Technical Small Business Owner's Guide",
        "price": "27",
        "description": """You've seen the headlines. AI will transform small business. Automate everything.

And then you try to set it up and it sounds like this: LLMs, API integrations, agent workflows...

You close the tab. You're busy running a business.

The Small Business AI Agent Starter Kit was built for you.

This is a plain-English guide for small business owners who want the real benefits of AI — time back, better communications, less admin — without needing a tech background.

What's inside:

THE GUIDE (PDF, 25+ pages) — Six chapters: what AI agents are, the 5 tasks every business should automate first, setting up your first AI agent step by step, 30 automations for common tasks, mistakes to avoid, and your 90-day adoption roadmap.

30 AUTOMATIONS WITH EXACT PROMPT TEMPLATES — 30 specific automation ideas for customer communication, marketing, operations, sales, and reporting. Each with a ready-to-use prompt.

90-DAY WEEK-BY-WEEK ADOPTION PLAN — A week-by-week roadmap from signed up to fully integrated.

The average business owner saves 8-15 hours per month. No tech background required. Works with free tools. Instant download.""",
        "file": str(BASE / "small-biz-ai-starter/small-biz-ai-starter-bundle.zip"),
        "slug": "small-biz-ai-starter",
    },
    {
        "name": "Faith-Fueled Teen — A 52-Week Christian Life Skills Journal for Teenagers",
        "price": "9.99",
        "description": """Most journals give teenagers lines. This one gives them a life framework.

Faith-Fueled Teen is a 52-week Christian journal for teenagers who are serious about growing in their faith, their skills, and who they're becoming. Each week: Scripture, a real reflection question, three action steps, and journal space.

Four Sections. One Year.

IDENTITY & FAITH (Weeks 1-13) — Who am I? Whose am I? Identity, faith, doubt, prayer, and purpose.

REAL LIFE SKILLS (Weeks 14-26) — Money, relationships, communication, time management, work ethic. The practical skills most teenagers never learn until they're adults.

BUILDING SOMETHING (Weeks 27-39) — Entrepreneurship, goal setting, leadership, side hustles, personal brand.

HARD SEASONS (Weeks 40-52) — Anxiety, depression, failure, loneliness, grief, comparison. This section walks through the hard stuff with Scripture and honest reflection.

52 complete weekly spreads. Real reflection questions. Three concrete action steps per week. Faith-centered without being preachy. Bold teen-friendly design.

Perfect for teenagers who journal, youth group settings, confirmation curriculum, graduation gifts. PDF download.""",
        "file": str(BASE / "faith-fueled-teen/faith-fueled-teen-gumroad.zip"),
        "slug": "faith-fueled-teen-journal",
    },
]


async def ss(page: Page, name: str):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
    except:
        pass


async def dump_page(page: Page, prefix=""):
    try:
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print(f"{prefix}Page (first 15 lines):")
        for line in lines[:15]:
            print(f"{prefix}  {line}")
        btns = page.locator("button")
        count = await btns.count()
        visible_btns = []
        for i in range(min(count, 15)):
            try:
                t = await btns.nth(i).inner_text()
                v = await btns.nth(i).is_visible()
                if v and t.strip():
                    visible_btns.append(t.strip()[:40])
            except:
                pass
        if visible_btns:
            print(f"{prefix}Buttons: {visible_btns}")
    except Exception as e:
        print(f"{prefix}dump error: {e}")


async def create_product(page: Page, product: dict) -> dict:
    name = product["name"]
    price = product["price"]
    description = product["description"]
    file_path = product["file"]
    slug = product["slug"]
    result = {"name": name, "success": False, "product_id": None, "url": None}

    print(f"\n{'='*60}")
    print(f"Creating: {name[:50]}...")

    if not Path(file_path).exists():
        print(f"  ❌ File not found: {file_path}")
        return result

    # Step 1: New product — select "Digital product" type first
    print("Step 1: Create (select Digital product type)...")
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_01_new.png")

    # Fill name
    try:
        name_input = page.locator('input[placeholder="Name of product"]').first
        await name_input.wait_for(state="visible", timeout=15000)
        await name_input.fill(name)
        print(f"  ✓ Name: {name[:40]}")
    except Exception as e:
        print(f"  ✗ Name failed: {e}")
        return result

    # Select "Digital product" type
    try:
        # Click the Digital product button
        digital_btn = page.locator('button:has-text("Digital product")').first
        await digital_btn.wait_for(state="visible", timeout=8000)
        await digital_btn.click()
        await page.wait_for_timeout(500)
        print(f"  ✓ Selected: Digital product")
    except Exception as e:
        print(f"  ⚠️ Digital product button not found: {e}")
        # Try clicking the first product type option
        try:
            first_type = page.locator('[role="radio"], [type="radio"], button[class*="product"]').first
            await first_type.click()
            print(f"  ✓ Selected first product type")
        except:
            pass

    # Click "Next: Customize"
    try:
        next_btn = page.locator('button:has-text("Next: Customize"), button:has-text("Next")').first
        await next_btn.wait_for(state="visible", timeout=8000)
        await next_btn.click()
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(3000)
        print(f"  ✓ Next clicked. URL: {page.url}")
    except Exception as e:
        print(f"  ✗ Next failed: {e}")
        await dump_page(page, "  ")

    await ss(page, f"{slug}_02_after_next.png")

    # Get product ID
    url = page.url
    product_id = None
    if "/products/" in url:
        pid = url.split("/products/")[1].split("/")[0].split("?")[0]
        if pid and pid != "new":
            product_id = pid
            result["product_id"] = product_id
            print(f"  ✓ Product ID: {product_id}")

    if not product_id:
        print(f"  ❌ No product ID. URL: {url}")
        await dump_page(page, "  ")
        return result

    # Step 2: Fill description on edit page
    print("Step 2: Description + price...")
    edit_url = f"https://gumroad.com/products/{product_id}/edit"
    await page.goto(edit_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_03_edit.png")

    # Description via contenteditable
    try:
        desc_editor = page.locator('[contenteditable="true"]').first
        await desc_editor.wait_for(state="visible", timeout=10000)
        await desc_editor.click()
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Delete")
        # Type description in chunks to avoid timeouts
        chunk_size = 500
        desc = description
        for i in range(0, len(desc), chunk_size):
            chunk = desc[i:i+chunk_size]
            await page.keyboard.type(chunk, delay=0)
        await page.wait_for_timeout(500)
        print(f"  ✓ Description ({len(description)} chars)")
    except Exception as e:
        print(f"  ⚠️ Description contenteditable: {e}")

    # Price
    try:
        # Look for price input more broadly
        price_selectors = [
            'input[name="price"]',
            'input[placeholder*="price" i]',
            'input[placeholder*="0.99"]',
            'input[placeholder*="$"]',
        ]
        price_filled = False
        for selector in price_selectors:
            try:
                inp = page.locator(selector).first
                if await inp.count() > 0:
                    await inp.wait_for(state="visible", timeout=3000)
                    await inp.click()
                    await page.keyboard.press("Meta+a")
                    await inp.fill(price)
                    price_filled = True
                    print(f"  ✓ Price ${price} via {selector}")
                    break
            except:
                continue

        if not price_filled:
            # Find inputs and try number-type ones
            all_inputs = page.locator('input[type="text"], input[type="number"]')
            cnt = await all_inputs.count()
            for i in range(min(cnt, 15)):
                inp = all_inputs.nth(i)
                try:
                    ph = await inp.get_attribute("placeholder") or ""
                    nm = await inp.get_attribute("name") or ""
                    if any(x in (ph + nm).lower() for x in ["price", "amount", "cost", "0.99"]):
                        await inp.click()
                        await page.keyboard.press("Meta+a")
                        await inp.fill(price)
                        print(f"  ✓ Price ${price} via input (ph='{ph}', name='{nm}')")
                        price_filled = True
                        break
                except:
                    continue
            if not price_filled:
                print(f"  ⚠️ Price field not found")
                await dump_page(page, "  ")
    except Exception as e:
        print(f"  ⚠️ Price: {e}")

    # Save product tab
    await ss(page, f"{slug}_04_before_save.png")
    try:
        save_btn = page.locator('button:has-text("Save and continue")').first
        await save_btn.wait_for(state="visible", timeout=8000)
        await save_btn.click()
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(2000)
        print(f"  ✓ Saved. URL: {page.url}")
    except Exception as e:
        print(f"  ⚠️ Save: {e}")

    await ss(page, f"{slug}_05_after_save.png")

    # Step 3: Upload file
    print("Step 3: Upload file...")
    content_url = f"https://gumroad.com/products/{product_id}/edit/content"
    await page.goto(content_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_06_content.png")

    file_uploaded = False
    try:
        fi = page.locator('input[type="file"]')
        fi_count = await fi.count()
        if fi_count > 0:
            print(f"  Uploading {Path(file_path).name} ({fi_count} inputs found)...")
            await fi.first.set_input_files(file_path)
            print("  Waiting for upload...")
            for i in range(36):
                await page.wait_for_timeout(5000)
                body_txt = await page.locator("body").inner_text()
                fname = Path(file_path).name
                if fname in body_txt or "100%" in body_txt or "uploaded" in body_txt.lower():
                    print(f"  ✓ Upload complete ({(i+1)*5}s)")
                    file_uploaded = True
                    break
                if i % 3 == 2:
                    print(f"  Still uploading... ({(i+1)*5}s)")
            if not file_uploaded:
                print(f"  ⚠️ Upload may still be in progress")
                file_uploaded = True  # Assume it worked
        else:
            # Try via file chooser
            upload_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload")').first
            if await upload_btn.count() > 0:
                print("  Using file chooser...")
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click()
                fc = await fc_info.value
                await fc.set_files(file_path)
                await page.wait_for_timeout(15000)
                file_uploaded = True
                print(f"  ✓ File chooser done")
            else:
                print("  ⚠️ No file upload mechanism found")
                await dump_page(page, "  ")
    except Exception as e:
        print(f"  ⚠️ Upload error: {e}")

    await ss(page, f"{slug}_07_after_upload.png")

    # Save content tab
    try:
        save_c = page.locator('button:has-text("Save and continue")').first
        if await save_c.count() > 0 and await save_c.is_visible():
            await save_c.click()
            await page.wait_for_timeout(3000)
            print("  ✓ Content saved")
    except:
        pass

    # Step 4: Navigate wizard to publish
    print("Step 4: Publishing...")
    for attempt in range(10):
        cur_url = page.url
        body = await page.locator("body").inner_text()

        if "Unpublish" in body:
            print(f"  ✅ ALREADY PUBLISHED")
            result["success"] = True
            break

        # Look for Publish button
        pub_btn = page.locator('button:has-text("Publish")').first
        if await pub_btn.count() > 0 and await pub_btn.is_visible():
            print(f"  → Clicking Publish (attempt {attempt+1})...")
            await pub_btn.click()
            await page.wait_for_timeout(5000)
            await ss(page, f"{slug}_pub_{attempt}.png")
            body2 = await page.locator("body").inner_text()
            if "Unpublish" in body2:
                print(f"  ✅ PUBLISHED!")
                result["success"] = True
            break

        # Look for Save and continue to advance wizard
        save_btn = page.locator('button:has-text("Save and continue")').first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            print(f"  → Advancing wizard (attempt {attempt+1})... URL: {cur_url}")
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            continue

        # Navigate to next step manually
        if "/edit" in cur_url and "/content" not in cur_url:
            next_url = f"https://gumroad.com/products/{product_id}/edit/content"
        elif "/content" in cur_url:
            next_url = f"https://gumroad.com/products/{product_id}/edit/receipt"
        elif "/receipt" in cur_url:
            next_url = f"https://gumroad.com/products/{product_id}/edit/share"
        else:
            next_url = f"https://gumroad.com/products/{product_id}/edit"
        print(f"  → Navigate to: {next_url}")
        await page.goto(next_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

    await ss(page, f"{slug}_09_final.png")

    result["product_id"] = product_id
    result["url"] = f"https://gumroad.com/products/{product_id}/edit"

    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Publishing Demand Products to Gumroad v3")

        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "sign" in page.url:
            print("❌ Not logged in!")
            return
        print(f"✓ Logged in: {page.url}")

        for product in PRODUCTS:
            r = await create_product(page, product)
            results.append(r)
            await page.wait_for_timeout(2000)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    for r in results:
        status = "✅" if r["success"] else "⚠️ "
        print(f"{status} {r['name'][:50]}")
        if r.get("product_id"):
            print(f"   ID: {r['product_id']}")
            print(f"   Edit: https://gumroad.com/products/{r['product_id']}/edit")

    # Save results
    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/DEMAND-PUBLISH-RESULTS.txt")
    with open(results_path, "w") as f:
        f.write("Demand Products — Gumroad Results\n")
        f.write("="*50 + "\n\n")
        for r in results:
            f.write(f"Product: {r['name']}\n")
            f.write(f"Status: {'PUBLISHED' if r['success'] else 'CREATED'}\n")
            f.write(f"ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit: https://gumroad.com/products/{r['product_id']}/edit\n")
            f.write("\n")
    print(f"Results: {results_path}")


asyncio.run(main())

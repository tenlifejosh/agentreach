"""
Publish 3 Demand Products to Gumroad
Uses exactly the proven pattern from publish_ai_operator_products_v2.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/demand_final_screenshots")
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

THE CHURCH AI TOOLKIT GUIDE (PDF, 20+ pages) — Step-by-step guidance: sermon prep, communications, small group curriculum, pastoral care, admin, and creating your church AI policy.

50 BIBLE-BASED AI PROMPTS — 50 ready-to-use prompts by ministry area. Sermon prep, social media, communications, small groups, pastoral care.

CHURCH AI POLICY TEMPLATE — A complete, customizable AI policy for your church.

Who this is for: Pastors who want to use AI without losing their voice. Church administrators drowning in communications. Ministry leaders who want to prepare better curriculum.

The printing press didn't replace the preacher. AI won't either — if you use it with wisdom.

Instant download. Three documents included.""",
        "file": str(BASE / "church-ai-toolkit/church-ai-toolkit-bundle.zip"),
        "slug": "church-ai-toolkit",
    },
    {
        "name": "AI Agent Starter Kit — The Non-Technical Small Business Owner's Guide",
        "price": "27",
        "description": """You've seen the headlines. AI will transform small business. Automate everything.

And then you try to set it up and it sounds like: LLMs, API integrations, agent workflows. You close the tab. You're busy running a business.

The Small Business AI Agent Starter Kit was built for you.

Plain-English guide for small business owners who want the real benefits of AI — time back, better communications, less admin — without needing a tech background.

What's inside:

THE GUIDE (PDF, 25+ pages) — Six chapters: what AI agents are, the 5 tasks to automate first, setting up your first AI agent step by step, 30 automations, mistakes to avoid, and your 90-day roadmap.

30 AUTOMATIONS WITH EXACT PROMPT TEMPLATES — Ready-to-use prompts for customer communication, marketing, operations, sales, and reporting.

90-DAY WEEK-BY-WEEK ADOPTION PLAN — From signed up to fully integrated.

The average business owner saves 8-15 hours per month. No tech background required. Instant download.""",
        "file": str(BASE / "small-biz-ai-starter/small-biz-ai-starter-bundle.zip"),
        "slug": "small-biz-ai-starter",
    },
    {
        "name": "Faith-Fueled Teen — A 52-Week Christian Life Skills Journal for Teenagers",
        "price": "9.99",
        "description": """Most journals give teenagers lines. This one gives them a life framework.

Faith-Fueled Teen is a 52-week Christian journal for teenagers serious about growing in faith, skills, and character. Each week: Scripture, a real reflection question, three action steps, and journal space.

Four Sections. One Year.

IDENTITY & FAITH (Weeks 1-13) — Who am I? Whose am I? Identity, faith, doubt, prayer, purpose.
REAL LIFE SKILLS (Weeks 14-26) — Money, relationships, communication, time management, work ethic.
BUILDING SOMETHING (Weeks 27-39) — Entrepreneurship, goal setting, leadership, side hustles.
HARD SEASONS (Weeks 40-52) — Anxiety, depression, failure, loneliness, grief — with Scripture and honest reflection.

52 complete weekly spreads. Real reflection questions. Three action steps per week. Bold teen-friendly design.

Perfect for teenagers who journal, youth groups, confirmation, graduation gifts. PDF download.""",
        "file": str(BASE / "faith-fueled-teen/faith-fueled-teen-gumroad.zip"),
        "slug": "faith-fueled-teen-journal",
    },
]


async def ss(page: Page, name: str):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
        print(f"  📸 {name}")
    except:
        pass


async def dump_page(page: Page, prefix=""):
    try:
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print(f"{prefix}Page text (first 25 lines):")
        for line in lines[:25]:
            print(f"{prefix}  {line}")
        btns = page.locator("button")
        count = await btns.count()
        visible_btns = []
        for i in range(min(count, 20)):
            try:
                t = await btns.nth(i).inner_text()
                v = await btns.nth(i).is_visible()
                if v and t.strip():
                    visible_btns.append(t.strip())
            except:
                pass
        if visible_btns:
            print(f"{prefix}Visible buttons: {visible_btns}")
    except Exception as e:
        print(f"{prefix}dump_page error: {e}")


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

    if not Path(file_path).exists():
        print(f"  ❌ File not found: {file_path}")
        return result

    # Step 1: Open new product form
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_01_new.png")

    # Fill product name
    try:
        name_input = page.locator('input[placeholder="Name of product"]').first
        await name_input.wait_for(state="visible", timeout=15000)
        await name_input.fill(name)
        await page.wait_for_timeout(300)
        print(f"  ✓ Name filled")
    except Exception as e:
        print(f"  ❌ Name input not found: {e}")
        await dump_page(page, "  ")
        return result

    # Fill price (may be on first page)
    try:
        price_input = page.locator('input[name="price"], input[placeholder*="rice"]').first
        await price_input.wait_for(state="visible", timeout=5000)
        await price_input.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await price_input.type(price)
        await page.wait_for_timeout(300)
        print(f"  ✓ Price filled: ${price}")
    except Exception as e:
        print(f"  ⚠️ Price field on page 1: {e}")

    # Click "Next" (first step of wizard)
    next_btn = page.locator('button:has-text("Next")').first
    try:
        await next_btn.wait_for(state="visible", timeout=10000)
        print("  Clicking Next...")
        await next_btn.click()
        await page.wait_for_timeout(2000)
        await ss(page, f"{slug}_02_after_next.png")
    except Exception as e:
        print(f"  ⚠️ Next button: {e}")
        await dump_page(page, "  ")

    # Try price again if visible on next step
    try:
        price_input2 = page.locator('input[name="price"], input[placeholder*="rice"]').first
        if await price_input2.is_visible():
            await price_input2.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Backspace")
            await price_input2.type(price)
            print(f"  ✓ Price set on step 2: ${price}")
    except:
        pass

    # Click Customize / Create product / Next: Customize
    for btn_text in ["Customize", "Create product", "Next: Customize", "Next"]:
        btn = page.locator(f'button:has-text("{btn_text}")').first
        if await btn.count() > 0 and await btn.is_visible():
            print(f"  Clicking '{btn_text}'...")
            await btn.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            break

    print(f"  URL after create: {page.url}")
    await ss(page, f"{slug}_03_after_create.png")

    # Extract product ID
    url = page.url
    product_id = None
    if "/products/" in url:
        pid = url.split("/products/")[1].split("/")[0].split("?")[0]
        if pid and pid != "new":
            product_id = pid
            result["product_id"] = product_id
            print(f"  ✓ Product ID: {product_id}")
        else:
            print("  ⚠️ Still on /products/new — dumping page:")
            await dump_page(page, "  ")

    if not product_id:
        print("  ❌ No product ID — cannot continue")
        return result

    # Step 2: Fill description
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
        print(f"  ✓ Description filled ({len(description)} chars)")
    except Exception as e:
        print(f"  ⚠️ Description: {e}")

    # Save Product tab
    await ss(page, f"{slug}_04_before_save.png")
    try:
        save_btn = page.locator('button:has-text("Save and continue")').first
        await save_btn.wait_for(state="visible", timeout=8000)
        await save_btn.click()
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(2000)
        print(f"  ✓ Product tab saved. URL: {page.url}")
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
            print(f"  File input found ({fi_count}), uploading {Path(file_path).name}...")
            await fi.first.set_input_files(file_path)
            print("  Waiting for upload...")
            for i in range(36):
                await page.wait_for_timeout(5000)
                body_txt = await page.locator("body").inner_text()
                fname = Path(file_path).name
                if fname in body_txt or "100%" in body_txt or "uploaded" in body_txt.lower():
                    print(f"  ✓ Upload complete")
                    file_uploaded = True
                    break
                if i % 3 == 2:
                    print(f"  Still uploading... ({(i+1)*5}s)")
        else:
            upload_btn = page.locator('button:has-text("Upload")').first
            if await upload_btn.count() > 0:
                print("  Using file chooser...")
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    await upload_btn.click()
                fc = await fc_info.value
                await fc.set_files(file_path)
                await page.wait_for_timeout(15000)
                file_uploaded = True
                print(f"  ✓ File set via chooser")
            else:
                print("  ⚠️ No upload mechanism found")
                await dump_page(page, "  ")
    except Exception as e:
        print(f"  ⚠️ Upload: {e}")

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

    # Step 4: Publish
    print("Step 4: Publishing...")
    for attempt in range(8):
        cur_url = page.url
        body = await page.locator("body").inner_text()

        if "Unpublish" in body:
            print(f"  ✅ PUBLISHED!")
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
                print(f"  ✅ PUBLISHED!")
                result["success"] = True
            break

        save_btn = page.locator('button:has-text("Save and continue")').first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            print(f"  Advance wizard (attempt {attempt+1})...")
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
        else:
            if "/content" not in cur_url:
                next_url = f"https://gumroad.com/products/{product_id}/edit/content"
            elif "/receipt" not in cur_url:
                next_url = f"https://gumroad.com/products/{product_id}/edit/receipt"
            elif "/share" not in cur_url:
                next_url = f"https://gumroad.com/products/{product_id}/edit/share"
            else:
                next_url = f"https://gumroad.com/products/{product_id}/edit"
            print(f"  Navigating to: {next_url}")
            await page.goto(next_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)

    await ss(page, f"{slug}_09_final.png")

    if result["success"] and product_id:
        result["url"] = f"https://gumroad.com/products/{product_id}/edit"

    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Publishing Demand Products to Gumroad (final)")

        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "sign" in page.url:
            print("❌ Not logged in!")
            return
        print(f"✓ Logged in at: {page.url}")

        for product in PRODUCTS:
            r = await create_product(page, product)
            results.append(r)
            await page.wait_for_timeout(2000)

    # Report
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)

    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/DEMAND-PUBLISH-RESULTS.txt")
    with open(results_path, "w") as f:
        f.write("Demand Products — Gumroad Publishing Results\n")
        f.write("="*60 + "\n\n")

        for r in results:
            status = "✅ PUBLISHED" if r["success"] else "❌ FAILED"
            print(f"\n{status}")
            print(f"  Product: {r['name']}")
            if r.get("product_id"):
                edit_url = f"https://gumroad.com/products/{r['product_id']}/edit"
                pub_url = f"https://tenlifejosh.gumroad.com/l/{r['product_id']}"
                print(f"  Edit: {edit_url}")
                print(f"  Public: {pub_url}")

            f.write(f"Product: {r['name']}\n")
            f.write(f"Status: {'PUBLISHED' if r['success'] else 'FAILED'}\n")
            f.write(f"ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit: https://gumroad.com/products/{r['product_id']}/edit\n")
                f.write(f"Public: https://tenlifejosh.gumroad.com/l/{r['product_id']}\n")
            f.write("-"*40 + "\n\n")

    print(f"\nResults: {results_path}")


asyncio.run(main())

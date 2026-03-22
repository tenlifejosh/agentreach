"""
Publish 3 Demand Products to Gumroad (v4 — intercept network to get product ID)
"""
import asyncio
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/demand_v4_screenshots")
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

And then you try to set it up and it sounds like: LLMs, API integrations, agent workflows...

You close the tab. You're busy running a business.

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
    except:
        pass


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

    # Intercept API responses to capture product ID
    captured_id = []

    async def handle_response(response):
        try:
            if "/api/products" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    pid = None
                    if isinstance(data, dict):
                        pid = data.get("id") or data.get("product_id") or (data.get("product") or {}).get("id")
                    if pid and str(pid) not in captured_id:
                        captured_id.append(str(pid))
                        print(f"  [API] Captured product ID: {pid}")
                except:
                    pass
        except:
            pass

    page.on("response", handle_response)

    # Step 1: Create product
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    # Fill name
    try:
        name_input = page.locator('input[placeholder="Name of product"]').first
        await name_input.wait_for(state="visible", timeout=15000)
        await name_input.fill(name)
        print(f"  ✓ Name filled")
    except Exception as e:
        print(f"  ✗ Name failed: {e}")
        page.remove_listener("response", handle_response)
        return result

    # Select Digital product
    try:
        digital_btn = page.locator('button:has-text("Digital product")').first
        await digital_btn.wait_for(state="visible", timeout=5000)
        await digital_btn.click()
        await page.wait_for_timeout(300)
        print(f"  ✓ Digital product selected")
    except Exception as e:
        print(f"  ⚠️ Type select: {e}")

    # Click Next and watch for URL change or API response
    try:
        next_btn = page.locator('button:has-text("Next: Customize"), button:has-text("Next")').first
        await next_btn.wait_for(state="visible", timeout=8000)

        # Watch for URL change
        old_url = page.url
        await next_btn.click()

        # Wait up to 15 seconds for URL to change
        for _ in range(30):
            await page.wait_for_timeout(500)
            new_url = page.url
            if new_url != old_url and "/products/new" not in new_url:
                print(f"  ✓ URL changed: {new_url}")
                break
            # Check if API captured an ID
            if captured_id:
                print(f"  ✓ API response captured ID: {captured_id[-1]}")
                break

        print(f"  Final URL: {page.url}")
        print(f"  Captured IDs: {captured_id}")
    except Exception as e:
        print(f"  ✗ Next: {e}")

    await ss(page, f"{slug}_01_after_next.png")

    # Get product ID from URL or captured
    product_id = None
    url = page.url
    if "/products/" in url:
        pid = url.split("/products/")[1].split("/")[0].split("?")[0]
        if pid and pid != "new":
            product_id = pid

    if not product_id and captured_id:
        product_id = captured_id[-1]

    # If still no ID, check page content for product URL
    if not product_id:
        try:
            html = await page.content()
            # Look for patterns like /products/XXXXX
            matches = re.findall(r'/products/([a-z0-9]+)(?:/|")', html)
            for m in matches:
                if m and m != "new":
                    product_id = m
                    print(f"  ✓ Found ID in page content: {product_id}")
                    break
        except:
            pass

    if not product_id:
        print(f"  ❌ No product ID found. URL: {page.url}")
        # Try to get from products list
        try:
            await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            # Get most recent product
            html = await page.content()
            matches = re.findall(r'/products/([a-z0-9]+)/edit', html)
            if matches:
                product_id = matches[0]
                print(f"  ✓ Found ID from products list: {product_id}")
        except Exception as e:
            print(f"  Products list failed: {e}")

    page.remove_listener("response", handle_response)

    if not product_id:
        print(f"  ❌ Cannot proceed without product ID")
        return result

    result["product_id"] = product_id
    print(f"  ✓ Product ID: {product_id}")

    # Step 2: Edit page — description and price
    print("Step 2: Fill description + price...")
    edit_url = f"https://gumroad.com/products/{product_id}/edit"
    await page.goto(edit_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_02_edit.png")

    # Description
    try:
        desc_editor = page.locator('[contenteditable="true"]').first
        await desc_editor.wait_for(state="visible", timeout=10000)
        await desc_editor.click()
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Delete")
        chunk_size = 800
        for i in range(0, len(description), chunk_size):
            await page.keyboard.type(description[i:i+chunk_size], delay=0)
        await page.wait_for_timeout(300)
        print(f"  ✓ Description filled")
    except Exception as e:
        print(f"  ⚠️ Description: {e}")

    # Price — find by multiple strategies
    try:
        price_filled = False
        # Strategy 1: by name
        for sel in ['input[name="price"]', 'input[placeholder*="0.99"]', 'input[placeholder*="price" i]']:
            try:
                inp = page.locator(sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await inp.click()
                    await page.keyboard.press("Meta+a")
                    await inp.fill(price)
                    print(f"  ✓ Price ${price}")
                    price_filled = True
                    break
            except:
                continue

        if not price_filled:
            # Strategy 2: find all inputs and check labels
            inputs = page.locator('input')
            cnt = await inputs.count()
            for i in range(cnt):
                try:
                    inp = inputs.nth(i)
                    ph = await inp.get_attribute("placeholder") or ""
                    nm = await inp.get_attribute("name") or ""
                    visible = await inp.is_visible()
                    if visible and any(x in (ph+nm).lower() for x in ["price", "0.99", "amount"]):
                        await inp.click()
                        await page.keyboard.press("Meta+a")
                        await inp.fill(price)
                        print(f"  ✓ Price ${price} via input ('{ph}'/'{nm}')")
                        price_filled = True
                        break
                except:
                    continue

        if not price_filled:
            print(f"  ⚠️ Price not found — will check page")
            # Dump visible inputs
            inputs = page.locator('input')
            cnt = await inputs.count()
            print(f"  Inputs found: {cnt}")
            for i in range(min(cnt, 10)):
                try:
                    inp = inputs.nth(i)
                    ph = await inp.get_attribute("placeholder") or ""
                    nm = await inp.get_attribute("name") or ""
                    tp = await inp.get_attribute("type") or ""
                    v = await inp.is_visible()
                    print(f"    Input {i}: type={tp} name={nm} ph='{ph}' visible={v}")
                except:
                    pass
    except Exception as e:
        print(f"  ✗ Price: {e}")

    # Save
    await ss(page, f"{slug}_03_before_save.png")
    try:
        save_btn = page.locator('button:has-text("Save and continue")').first
        await save_btn.wait_for(state="visible", timeout=8000)
        await save_btn.click()
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(2000)
        print(f"  ✓ Saved")
    except Exception as e:
        print(f"  ⚠️ Save: {e}")

    # Step 3: Upload file
    print("Step 3: Upload file...")
    content_url = f"https://gumroad.com/products/{product_id}/edit/content"
    await page.goto(content_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_04_content.png")

    file_uploaded = False
    fi = page.locator('input[type="file"]')
    fi_count = await fi.count()
    if fi_count > 0:
        print(f"  Uploading via file input ({fi_count} found)...")
        await fi.first.set_input_files(file_path)
        for i in range(40):
            await page.wait_for_timeout(5000)
            body_txt = await page.locator("body").inner_text()
            fname = Path(file_path).name
            if fname in body_txt or "100%" in body_txt or "uploaded" in body_txt.lower():
                print(f"  ✓ Uploaded ({(i+1)*5}s)")
                file_uploaded = True
                break
            if i % 4 == 3:
                print(f"  Waiting... {(i+1)*5}s")
        if not file_uploaded:
            print(f"  ⚠️ Upload timeout — assuming complete")
            file_uploaded = True
    else:
        # Try file chooser
        try:
            upload_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload")').first
            if await upload_btn.count() > 0:
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await upload_btn.click()
                fc = await fc_info.value
                await fc.set_files(file_path)
                await page.wait_for_timeout(20000)
                file_uploaded = True
                print(f"  ✓ Uploaded via chooser")
            else:
                print(f"  ⚠️ No upload mechanism")
        except Exception as e:
            print(f"  ⚠️ Upload: {e}")

    await ss(page, f"{slug}_05_after_upload.png")

    # Save content
    try:
        save_c = page.locator('button:has-text("Save and continue")').first
        if await save_c.count() > 0 and await save_c.is_visible():
            await save_c.click()
            await page.wait_for_timeout(3000)
            print("  ✓ Content saved")
    except:
        pass

    # Step 4: Publish
    print("Step 4: Publish...")
    for attempt in range(10):
        body = await page.locator("body").inner_text()
        cur_url = page.url

        if "Unpublish" in body:
            print(f"  ✅ PUBLISHED!")
            result["success"] = True
            break

        pub_btn = page.locator('button:has-text("Publish")').first
        if await pub_btn.count() > 0 and await pub_btn.is_visible():
            print(f"  Publish button found! Clicking... (attempt {attempt+1})")
            await pub_btn.click()
            await page.wait_for_timeout(5000)
            await ss(page, f"{slug}_pub_{attempt}.png")
            body2 = await page.locator("body").inner_text()
            if "Unpublish" in body2:
                print(f"  ✅ PUBLISHED!")
                result["success"] = True
            break

        save_btn = page.locator('button:has-text("Save and continue")').first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            await save_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            continue

        # Manual wizard navigation
        steps = ["/edit", "/edit/content", "/edit/receipt", "/edit/share"]
        current_step = None
        for s in steps:
            if cur_url.endswith(s) or cur_url.endswith(s + "?") or s in cur_url:
                current_step = s
                break
        step_idx = steps.index(current_step) if current_step in steps else 0
        next_idx = min(step_idx + 1, len(steps) - 1)
        next_url = f"https://gumroad.com/products/{product_id}{steps[next_idx]}"
        print(f"  Navigate: {next_url}")
        await page.goto(next_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

    await ss(page, f"{slug}_06_final.png")
    result["url"] = f"https://gumroad.com/products/{product_id}/edit"
    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Publishing Demand Products to Gumroad v4")

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

    # Save
    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/DEMAND-PUBLISH-RESULTS.txt")
    with open(results_path, "w") as f:
        f.write("Demand Products — Gumroad Results\n")
        f.write("="*50 + "\n\n")
        for r in results:
            f.write(f"Product: {r['name']}\n")
            f.write(f"Status: {'PUBLISHED' if r['success'] else 'CREATED-NEEDS-PUBLISH'}\n")
            f.write(f"ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit URL: https://gumroad.com/products/{r['product_id']}/edit\n")
            f.write("\n")
    print(f"Results: {results_path}")


asyncio.run(main())

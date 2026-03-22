"""
Publish 3 Demand Products to Gumroad (v2 — matches proven publish_ai_operator_products_v2 flow)
1. Church AI Toolkit — $37
2. AI Agent Starter Kit — $27
3. Faith-Fueled Teen Journal — $9.99
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/demand_v2_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

BASE = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products")

PRODUCTS = [
    {
        "name": "Church AI Toolkit — 50 Bible-Based Prompts + Ministry Templates",
        "price": "37",
        "description": """You've probably already used AI. Maybe you asked it to help with a sermon illustration, or draft a newsletter you didn't have time to write. But if you're like most church leaders, you're doing it without a system — a little here, a little there, quietly, because you're not sure what the rules are.

This toolkit gives you the framework.

The Church AI Toolkit is a complete guide for pastors, ministry directors, church staff, and volunteer leaders who want to use artificial intelligence as a ministry tool — without compromising authenticity, theological integrity, or the irreplaceable work of the Holy Spirit.

What's included:

THE CHURCH AI TOOLKIT GUIDE (PDF, 20+ pages)
Step-by-step guidance for using AI across every area of church ministry: sermon prep, church communications, small group curriculum, pastoral care communications, admin, and how to create your church AI policy.

50 BIBLE-BASED AI PROMPTS (50-PROMPTS.md)
50 ready-to-use prompts organized by ministry area — copy, fill in the details, get results. Sermon prep, social media, communications, small groups, pastoral care.

CHURCH AI POLICY TEMPLATE (CHURCH-AI-POLICY-TEMPLATE.md)
A complete, customizable AI policy for your church — covering permitted uses, prohibited uses, privacy protection, theological review standards, and team accountability.

Who this is for: Pastors who want to use AI without losing their voice. Church administrators drowning in communications. Ministry leaders who want to prepare better curriculum.

The printing press didn't replace the preacher. The microphone didn't replace the anointing. AI won't either — if you use it with wisdom.

Instant download. Three documents included.""",
        "file": str(BASE / "church-ai-toolkit/church-ai-toolkit-bundle.zip"),
        "slug": "church-ai-toolkit",
    },
    {
        "name": "AI Agent Starter Kit — The Non-Technical Small Business Owner's Guide",
        "price": "27",
        "description": """You've seen the headlines. "AI will transform small business." "Automate everything." "10x your productivity."

And then you go to actually set it up and it sounds like this: LLMs, API integrations, agent workflows, automation stacks...

You close the tab. You're busy running a business.

The Small Business AI Agent Starter Kit was built for you.

This is a plain-English guide for small business owners who want the real benefits of AI — time back, better communications, less admin — without needing a tech background or a developer on staff.

What's inside:

THE GUIDE (PDF, 25+ pages)
Six chapters: what AI agents actually are, the 5 tasks every small business should automate first, setting up your first AI agent step by step, 30 automations for common business tasks, mistakes to avoid, and your 90-day adoption roadmap.

30 AUTOMATIONS WITH EXACT PROMPT TEMPLATES
30 specific automation ideas for customer communication, marketing, operations, sales, and reporting — each with a ready-to-use prompt. Copy, fill in your details, paste into ChatGPT or Claude.

90-DAY WEEK-BY-WEEK ADOPTION PLAN
A week-by-week roadmap from signed up to fully integrated.

The average small business owner who follows this guide saves 8-15 hours per month.

No tech background required. Works with free tools. Start today. Instant download.""",
        "file": str(BASE / "small-biz-ai-starter/small-biz-ai-starter-bundle.zip"),
        "slug": "small-biz-ai-starter",
    },
    {
        "name": "Faith-Fueled Teen — A 52-Week Christian Life Skills Journal for Teenagers",
        "price": "9.99",
        "description": """Most journals give teenagers lines. This one gives them a life framework.

Faith-Fueled Teen is a 52-week Christian journal for teenagers who are serious about growing — in their faith, in their skills, and in who they're becoming. Each week: Scripture, a real reflection question, three action steps, and journal space.

Four Sections. One Year.

SECTION 1: IDENTITY & FAITH (Weeks 1-13)
Who am I? Whose am I? What do I actually believe? Identity, faith, doubt, prayer, and purpose.

SECTION 2: REAL LIFE SKILLS (Weeks 14-26)
Money, relationships, communication, time management, work ethic. The practical skills most teenagers never learn until they're adults.

SECTION 3: BUILDING SOMETHING (Weeks 27-39)
Entrepreneurship, goal setting, leadership, side hustles, networking, personal brand.

SECTION 4: HARD SEASONS (Weeks 40-52)
Anxiety, depression, failure, loneliness, grief, comparison. This section walks through the hard stuff with Scripture and honest reflection.

52 complete weekly spreads. Real reflection questions. Three concrete action steps per week. Faith-centered without being preachy.

Perfect for: teenagers who journal, youth group settings, confirmation curriculum, graduation gifts.

This is the journal someone should have given you years ago. PDF download.""",
        "file": str(BASE / "faith-fueled-teen/faith-fueled-teen-gumroad.zip"),
        "slug": "faith-fueled-teen-journal",
    },
]


async def ss(page: Page, name: str):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
        print(f"  📸 {name}")
    except Exception as e:
        print(f"  [ss failed: {e}]")


async def dump_page(page: Page, prefix=""):
    try:
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        print(f"{prefix}Page text (first 20 lines):")
        for line in lines[:20]:
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
    print(f"Creating: {name[:50]}...")
    print(f"{'='*60}")

    if not Path(file_path).exists():
        print(f"  ❌ File not found: {file_path}")
        return result

    # Step 1: Create product with name
    print("Step 1: Create new product...")
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_01_new.png")

    # Fill product name
    try:
        name_input = page.locator('input[placeholder="Name of product"]').first
        await name_input.wait_for(state="visible", timeout=15000)
        await name_input.fill(name)
        print(f"  ✓ Name filled")
    except Exception as e:
        print(f"  ✗ Name fill failed: {e}")
        await dump_page(page, "  ")
        return result

    # Click "Next: Customize" to advance wizard
    try:
        next_btn = page.locator('button:has-text("Next"), button:has-text("Customize"), button:has-text("Next: Customize")').first
        await next_btn.wait_for(state="visible", timeout=8000)
        await next_btn.click()
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        print(f"  ✓ Advanced wizard. URL: {page.url}")
    except Exception as e:
        print(f"  ⚠️ Next button not found, trying direct navigation... {e}")

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
        else:
            print("  ⚠️ Still on /products/new — dumping page:")
            await dump_page(page, "  ")

    if not product_id:
        print("  ❌ No product ID — cannot continue")
        return result

    # Step 2: Fill description and price on edit page
    print("Step 2: Fill description and price...")
    edit_url = f"https://gumroad.com/products/{product_id}/edit"
    await page.goto(edit_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_03_edit.png")

    # Fill description (contenteditable)
    try:
        desc_editor = page.locator('[contenteditable="true"]').first
        await desc_editor.wait_for(state="visible", timeout=10000)
        await desc_editor.click()
        await page.keyboard.press("Meta+a")
        await page.keyboard.type(description[:3000], delay=1)  # Limit to avoid timeout
        await page.wait_for_timeout(500)
        print(f"  ✓ Description filled")
    except Exception as e:
        print(f"  ⚠️ Description via contenteditable: {e}")
        # Try textarea
        try:
            ta = page.locator('textarea').first
            await ta.fill(description[:3000])
            print(f"  ✓ Description via textarea")
        except Exception as e2:
            print(f"  ✗ Description failed: {e2}")

    # Fill price
    try:
        price_input = page.locator('input[name="price"], input[placeholder*="0.99"], input[placeholder*="price"]').first
        await price_input.wait_for(state="visible", timeout=8000)
        await price_input.click()
        await page.keyboard.press("Meta+a")
        await price_input.fill(price)
        print(f"  ✓ Price filled: ${price}")
    except Exception as e:
        print(f"  ⚠️ Price field: {e}")
        # Try finding any number input
        try:
            inputs = page.locator('input[type="number"], input[type="text"]')
            count = await inputs.count()
            for i in range(min(count, 10)):
                inp = inputs.nth(i)
                placeholder = await inp.get_attribute("placeholder") or ""
                if any(x in placeholder.lower() for x in ["price", "$", "0.99", "amount"]):
                    await inp.click()
                    await page.keyboard.press("Meta+a")
                    await inp.fill(price)
                    print(f"  ✓ Price via input #{i}")
                    break
        except Exception as e2:
            print(f"  ✗ Price failed: {e2}")

    # Save
    await ss(page, f"{slug}_04_before_save.png")
    try:
        save_btn = page.locator('button:has-text("Save and continue"), button:has-text("Save")').first
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
                    await ss(page, f"{slug}_upload_{i}.png")
        else:
            # Try file chooser via button
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

    # Save content tab
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
            await ss(page, f"{slug}_08_after_publish_{attempt}.png")
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

    if product_id:
        result["url"] = f"https://gumroad.com/products/{product_id}/edit"
        result["product_id"] = product_id

    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Publishing Demand Products to Gumroad")

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
            status = "✅ PUBLISHED" if r["success"] else "⚠️  CREATED (verify)"
            print(f"\n{status}: {r['name'][:50]}")
            if r.get("product_id"):
                edit_url = f"https://gumroad.com/products/{r['product_id']}/edit"
                print(f"  Edit: {edit_url}")
            if r.get("url"):
                print(f"  URL: {r['url']}")

            f.write(f"Product: {r['name']}\n")
            f.write(f"Status: {'PUBLISHED' if r['success'] else 'CREATED-VERIFY'}\n")
            f.write(f"Product ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit URL: https://gumroad.com/products/{r['product_id']}/edit\n")
            f.write("-"*40 + "\n\n")

    print(f"\nResults: {results_path}")


asyncio.run(main())

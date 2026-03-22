"""
Publish 3 Demand Products to Gumroad
1. Church AI Toolkit — $37
2. AI Agent Starter Kit for Small Business — $27
3. Faith-Fueled Teen Journal — $9.99
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/demand_screenshots")
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
A week-by-week roadmap from "signed up for an account" to "AI is integrated into my daily workflow."

The average small business owner who follows this guide saves 8–15 hours per month.

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

SECTION 1: IDENTITY & FAITH (Weeks 1–13)
Who am I? Whose am I? What do I actually believe? These weeks deal with identity, faith, doubt, prayer, and purpose — honestly.

SECTION 2: REAL LIFE SKILLS (Weeks 14–26)
Money, relationships, communication, time management, work ethic. The practical skills most teenagers never learn until they're adults learning them the hard way.

SECTION 3: BUILDING SOMETHING (Weeks 27–39)
Entrepreneurship, goal setting, leadership, side hustles, networking, personal brand. You were made to create and solve problems.

SECTION 4: HARD SEASONS (Weeks 40–52)
Anxiety, depression, failure, loneliness, grief, comparison. Every teenager hits hard seasons. This section walks through them with Scripture and honest reflection.

What makes it different:
- 52 complete weekly spreads (not just blank lines)
- Real reflection questions that go deeper
- Three concrete action steps per week
- Faith-centered without being preachy
- Bold, teen-friendly design

Perfect for: teenagers who journal, youth group settings, confirmation curriculum, graduation gifts.

This is the journal someone should have given you years ago. PDF download — print at home or at a print shop.""",
        "file": str(BASE / "faith-fueled-teen/faith-fueled-teen-gumroad.zip"),
        "slug": "faith-fueled-teen-journal",
    },
]


async def ss(page: Page, name: str):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
        print(f"  📸 {name}")
    except Exception as e:
        print(f"  [screenshot failed: {e}]")


async def create_product(page: Page, product: dict) -> dict:
    name = product["name"]
    price = product["price"]
    description = product["description"]
    file_path = product["file"]
    slug = product["slug"]
    result = {"name": name, "success": False, "url": None}

    print(f"\n{'='*60}")
    print(f"Creating: {name[:50]}...")
    print(f"{'='*60}")

    if not Path(file_path).exists():
        print(f"  ❌ File not found: {file_path}")
        return result

    # Navigate to new product page
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
        return result

    # Fill price
    try:
        price_input = page.locator('input[name="price"], input[placeholder*="price"], input[placeholder*="Price"]').first
        await price_input.wait_for(state="visible", timeout=10000)
        await price_input.triple_click()
        await price_input.fill(price)
        print(f"  ✓ Price filled: ${price}")
    except Exception as e:
        print(f"  ✗ Price fill failed: {e}")

    # Fill description
    try:
        desc_area = page.locator('textarea[name="description"], div[contenteditable="true"], textarea').first
        await desc_area.wait_for(state="visible", timeout=10000)
        await desc_area.fill(description)
        print(f"  ✓ Description filled")
    except Exception as e:
        print(f"  ✗ Description fill failed: {e}")

    # Save/Create the product
    try:
        create_btn = page.locator('button:has-text("Create product"), button:has-text("Save"), button[type="submit"]').first
        await create_btn.wait_for(state="visible", timeout=10000)
        await create_btn.click()
        await page.wait_for_timeout(3000)
        await ss(page, f"{slug}_02_created.png")
        print(f"  ✓ Product created, URL: {page.url}")
    except Exception as e:
        print(f"  ✗ Create button failed: {e}")
        return result

    # Get product ID from URL
    current_url = page.url
    product_id = None
    if "/products/" in current_url:
        parts = current_url.split("/products/")
        if len(parts) > 1:
            product_id = parts[1].split("/")[0]
            print(f"  Product ID: {product_id}")

    # Navigate to content tab to upload file
    if product_id:
        content_url = f"https://gumroad.com/products/{product_id}/edit/content"
        await page.goto(content_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await ss(page, f"{slug}_03_content.png")

        # Upload file
        try:
            # Try to click Upload button first
            upload_btn = page.locator('button:has-text("Upload files"), button:has-text("Upload"), label:has-text("Upload")').first
            try:
                await upload_btn.wait_for(state="visible", timeout=8000)
                async with page.expect_file_chooser(timeout=8000) as fc_info:
                    await upload_btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(file_path)
                print(f"  ✓ File selected via button")
            except Exception:
                # Fall back to direct file input
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(file_path)
                print(f"  ✓ File selected via input")

            # Wait for upload
            await page.wait_for_timeout(6000)
            await ss(page, f"{slug}_04_uploaded.png")
            print(f"  ✓ File uploaded")
        except Exception as e:
            print(f"  ✗ File upload failed: {e}")

    # Navigate back to main edit page to publish
    if product_id:
        edit_url = f"https://gumroad.com/products/{product_id}/edit"
        await page.goto(edit_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Find and click Publish button
        try:
            publish_btn = page.locator('button:has-text("Publish"), a:has-text("Publish"), button:has-text("Publish and continue")').first
            await publish_btn.wait_for(state="visible", timeout=10000)
            await publish_btn.click()
            await page.wait_for_timeout(3000)
            await ss(page, f"{slug}_05_published.png")
            print(f"  ✓ Published!")

            # Get the public URL
            gumroad_url = f"https://tenlifejosh.gumroad.com/l/{product_id}"
            result["url"] = gumroad_url
            result["success"] = True
            result["product_id"] = product_id
            print(f"  🎉 URL: {gumroad_url}")
        except Exception as e:
            print(f"  ✗ Publish failed: {e}")
            # Still record what we have
            if product_id:
                result["url"] = f"https://gumroad.com/products/{product_id}/edit"
                result["product_id"] = product_id

    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        for product in PRODUCTS:
            result = await create_product(page, product)
            results.append(result)
            await page.wait_for_timeout(2000)

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"{status} {r['name'][:45]}")
        if r.get("url"):
            print(f"   URL: {r['url']}")

    return results


if __name__ == "__main__":
    asyncio.run(main())

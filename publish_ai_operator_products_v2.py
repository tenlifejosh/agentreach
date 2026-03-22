"""
Publish 3 AI Operator Products to Gumroad (v2 — using proven flow)
1. The AI Company OS Starter Kit — $97
2. The Complete Agent Skill Bundle — $47
3. AgentReach Setup Guide — $27
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault
from playwright.async_api import Page

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/ai_products_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

BASE = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products")

PRODUCTS = [
    {
        "name": "The AI Company OS Starter Kit — Run Your Business Like a Machine",
        "price": "97",
        "description": "You've probably heard the pitch before: use AI to run your business. What nobody tells you is that AI without a system is just expensive chaos.\n\nWe built the system.\n\nOver 7 weeks of real operations inside a 14-agent AI company, we developed what is now the most complete AI-powered business operating system ever made publicly available. Every decision, every workflow, every role — documented, tested, and refined in production. This is that system, packaged for you to install in a day.\n\nWhat's included:\n\n- 21 operational documents: your constitution, org chart, workflow playbook, approval matrix, escalation rules, handoff templates, intake classification system, and more\n- 14 role charters: detailed operating instructions for each AI agent role — COO, Architect, Scribe, Scout, Navigator, Analyst, Designer, Publisher, Social, Sentinel, Guardian, Steward, Closer, Librarian\n- The START-HERE onboarding guide — how your agent learns the OS on first session\n- Day 1 Setup checklist — go from zero to fully operational in 90 minutes\n\nWho this is for:\n\nFounders running lean who want AI doing the heavy lifting. Solopreneurs building systems that scale without headcount. Agency owners who want AI agents that operate like a trained team. AI builders who want a proven architecture.\n\nWhy it works:\n\nMost people give their AI a personality and a few instructions, then wonder why it's inconsistent. The problem isn't the AI — it's the absence of a real operating system. This OS gives your agent a constitution, a command structure, workflows, and role charters. That's how you get consistent, professional output.\n\nThe same architecture powers a real company with 14 active agents. That's the proof of concept. You're buying the blueprint.\n\nWorks with: OpenClaw (primary), adaptable to any AI agent platform. Instant download. No subscription.",
        "file": str(BASE / "tlc-os-starter/tlc-company-os-starter-kit.zip"),
        "slug": "ai-company-os-starter-kit",
    },
    {
        "name": "The Complete AI Agent Skill Bundle — 7 World-Class Skills for OpenClaw",
        "price": "47",
        "description": "Seven complete skill packages. Hundreds of hours of domain expertise. Drop them into OpenClaw and your agents gain world-class capability instantly.\n\nThis bundle contains the full skill stack used to run a 14-agent AI company — design, sales, social media, knowledge management, analytics, admin ops, and Reddit growth.\n\nWhat's included:\n\n- Graphic Design Mastery — 14 design domains: brand identity, typography, layout, social marketing, print production, UI/UX, illustration, data visualization, motion, generative design\n- Sales Mastery — 18 sales domains: outbound, discovery, objection handling, proposals, negotiation, CRM workflows, closing frameworks\n- Steward Ops — 14 operational domains: admin, scheduling, vendor relations, process documentation, compliance, reporting\n- Librarian Mastery — 14 knowledge domains: information architecture, tagging, research protocols, knowledge capture, retrieval\n- Analyst Mastery — 15 analytical domains: revenue analysis, market research, competitive intelligence, data modeling, reporting\n- Social Manager — Full social media playbook: strategy, content calendars, platform optimization, engagement systems, growth\n- Reddit Master — 734 lines of Reddit mastery: community building, organic growth, content strategy, engagement, platform rules\n\nHow to install: Drop the skill folder into your OpenClaw workspace. Your agent reads it automatically when the task matches the domain.\n\nCompatible with: OpenClaw (required). Instant download. Use across unlimited projects.",
        "file": str(BASE / "skill-bundle/tlc-complete-skill-bundle.zip"),
        "slug": "complete-ai-agent-skill-bundle",
    },
    {
        "name": "AgentReach Setup Guide — Automate Your Digital Product Platforms",
        "price": "27",
        "description": "Your AI agent can write the listing. It can generate the product. But without AgentReach, it still needs you to click publish.\n\nAgentReach is an open-source tool that gives your AI agents authenticated browser sessions for KDP, Gumroad, Etsy, Pinterest, and Reddit — no manual login required, no API keys needed, no paid service. Your agent harvests your session once, and from that point operates those platforms autonomously.\n\nThis guide covers everything (30 pages):\n\n- What AgentReach is — the architecture, how session harvesting works, why it beats API-only approaches\n- Installation walkthrough — step-by-step setup on macOS\n- Platform harvesting guides — how to capture sessions for KDP, Gumroad, Etsy, Pinterest, and Reddit\n- Common issues and fixes — the 10 most frequent problems and solutions\n- Real-world use cases — how a 14-agent AI company uses AgentReach to publish across 5 platforms\n- OpenClaw integration — connect AgentReach to your agent workflows so publishing becomes a single command\n\nWho this is for: Creators and founders who want their AI agents to close the loop — from building a product to having it live — without human intervention.\n\nAgentReach is free and open source. This guide is the fast path to making it work.\n\nInstant download. PDF format.",
        "file": str(BASE / "agentreach-guide/agentreach-setup-guide.pdf"),
        "slug": "agentreach-setup-guide",
    },
]


async def ss(page: Page, name: str):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=True)
        print(f"  📸 {name}")
    except:
        pass


async def dump_page(page: Page, prefix=""):
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

    # Fill price
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
        print(f"  ⚠️ Price field: {e}")

    # Click Next
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
        print("🚀 Publishing AI Operator Products to Gumroad (v2)")

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
    print("FINAL RESULTS — AI Operator Products")
    print("="*60)

    results_path = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/PUBLISH-RESULTS.txt")
    with open(results_path, "w") as f:
        f.write("AI Operator Products — Gumroad Publishing Results\n")
        f.write("="*60 + "\n\n")

        for r in results:
            status = "✅ PUBLISHED" if r["success"] else "❌ FAILED"
            print(f"\n{status}")
            print(f"  Product: {r['name']}")
            if r.get("product_id"):
                edit_url = f"https://gumroad.com/products/{r['product_id']}/edit"
                print(f"  Edit URL: {edit_url}")
            if r.get("url"):
                print(f"  Dashboard: {r['url']}")

            f.write(f"Product: {r['name']}\n")
            f.write(f"Status: {'PUBLISHED' if r['success'] else 'FAILED'}\n")
            f.write(f"Product ID: {r.get('product_id', 'N/A')}\n")
            if r.get("product_id"):
                f.write(f"Edit URL: https://gumroad.com/products/{r['product_id']}/edit\n")
            f.write("-"*40 + "\n\n")

    print(f"\nResults saved: {results_path}")


asyncio.run(main())

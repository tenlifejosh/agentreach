"""
Publish 3 AI Operator Products to Gumroad:
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

SCREENSHOTS_DIR = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/ai_products_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

BASE = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products")

PRODUCTS = [
    {
        "name": "The AI Company OS Starter Kit — Run Your Business Like a Machine",
        "price": "97",
        "description": """You've probably heard the pitch before: "use AI to run your business." What nobody tells you is that AI without a system is just expensive chaos.

We built the system.

Over 7 weeks of real operations inside a 14-agent AI company, we developed what is now the most complete AI-powered business operating system ever made publicly available. Every decision, every workflow, every role — documented, tested, and refined in production. This is that system, packaged for you to install in a day.

What's included:

• 21 operational documents — your constitution, org chart, workflow playbook, approval matrix, escalation rules, handoff templates, intake classification system, and more
• 14 role charters — detailed operating instructions for each AI agent role: COO, Architect, Scribe, Scout, Navigator, Analyst, Designer, Publisher, Social, Sentinel, Guardian, Steward, Closer, and Librarian
• The START-HERE onboarding guide — how your agent learns the OS on first session
• Day 1 Setup checklist — go from zero to fully operational in 90 minutes

Who this is for:

Founders running lean operations who want AI doing the heavy lifting. Solopreneurs building systems that scale without headcount. Agency owners who want their AI agents to operate like a trained team. AI builders who want a proven architecture instead of starting from scratch.

Why this works:

Most people give their AI a personality and a few instructions. Then wonder why it's inconsistent, needs hand-holding, and forgets context between sessions. The problem isn't the AI — it's the absence of a real operating system.

This OS gives your agent a constitution (governing law), a command structure (who decides what), a set of workflows (how work actually moves), and a role charter (what it owns). That's how you get an agent that operates like a professional, not an assistant.

The same architecture powers a company shipping digital products, running social media, managing research operations, and publishing content — all with minimal founder involvement. That's the proof of concept. You're buying the blueprint.

Works with: OpenClaw (primary), adaptable to any AI agent platform with persistent context support.

Instant download. No subscription. Yours to keep and customize.""",
        "file": str(BASE / "tlc-os-starter/tlc-company-os-starter-kit.zip"),
        "slug": "ai-company-os-starter-kit",
    },
    {
        "name": "The Complete AI Agent Skill Bundle — 7 World-Class Skills for OpenClaw",
        "price": "47",
        "description": """Seven complete skill packages. Hundreds of hours of domain expertise. Drop them into OpenClaw and your agents gain world-class capability instantly.

This bundle contains the full skill stack used to run a 14-agent AI company — design, sales, social media, knowledge management, analytics, admin ops, and Reddit growth. Each skill is a structured knowledge system: reference files, playbooks, and domain-specific frameworks that transform a general AI agent into a specialist.

What's included:

• Graphic Design Mastery — 14 design domains: brand identity, typography, layout, social marketing, print production, UI/UX, illustration, data visualization, motion, generative design, and more
• Sales Mastery — 18 sales domains: outbound strategy, discovery, objection handling, proposal writing, negotiation, follow-up systems, CRM workflows, and closing frameworks
• Steward Ops — 14 operational domains: admin management, scheduling, vendor relations, process documentation, compliance, reporting, and operational excellence
• Librarian Mastery — 14 knowledge domains: information architecture, tagging systems, research protocols, knowledge capture, retrieval optimization, and institutional memory
• Analyst Mastery — 15 analytical domains: revenue analysis, market research, competitive intelligence, data modeling, reporting frameworks, and strategic analysis
• Social Manager — Full social media playbook covering strategy, content calendars, platform-specific optimization, engagement systems, and growth tactics
• Reddit Master — 734 lines of Reddit-specific mastery: community building, organic growth, content strategy, engagement tactics, and platform rules

How to install: Drop the skill folder into your OpenClaw workspace. Your agent reads it automatically when the task matches the skill domain.

Compatible with: OpenClaw (required). Each skill uses OpenClaw's SKILL.md architecture.

Instant download. Use across unlimited projects.""",
        "file": str(BASE / "skill-bundle/tlc-complete-skill-bundle.zip"),
        "slug": "complete-ai-agent-skill-bundle",
    },
    {
        "name": "AgentReach Setup Guide — Automate Your Digital Product Platforms",
        "price": "27",
        "description": """Your AI agent can write the listing. It can generate the product. But without AgentReach, it still needs you to click "publish."

AgentReach is an open-source tool that gives your AI agents authenticated browser sessions for KDP, Gumroad, Etsy, Pinterest, and Reddit — no manual login required, no API keys needed, no paid third-party service. Your agent harvests your browser session once, and from that point on, it operates those platforms autonomously.

This guide covers everything:

What's inside (30 pages):

• What AgentReach is — the architecture, how session harvesting works, why it's more reliable than API-only approaches
• Installation walkthrough — step-by-step setup on macOS, full environment configuration
• Platform harvesting guides — exactly how to capture authenticated sessions for each platform: KDP, Gumroad, Etsy, Pinterest, and Reddit
• Common issues and fixes — the 10 most frequent problems and how to solve them
• Real-world use cases — how a 14-agent AI company uses AgentReach to publish, update, and manage products across 5 platforms
• OpenClaw integration — how to connect AgentReach sessions to your agent workflows so publishing becomes a single agent command

Who this is for: Creators and founders who want their AI agents to close the loop — from building a product to having it live on a platform — without human intervention.

AgentReach is free and open source. This guide is the fast path to making it work.

Instant download. PDF format.""",
        "file": str(BASE / "agentreach-guide/agentreach-setup-guide.pdf"),
        "slug": "agentreach-setup-guide",
    },
]


async def ss(page, name):
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR / name), full_page=False)
    except:
        pass


async def dump_page(page, prefix=""):
    try:
        body = await page.locator("body").inner_text()
        lines = [l.strip() for l in body.split("\n") if l.strip()][:30]
        for l in lines:
            print(f"{prefix}  | {l}")
    except:
        pass


async def create_product(page, product: dict) -> dict:
    name = product["name"]
    price = product["price"]
    desc = product["description"]
    file_path = product["file"]
    slug = product["slug"]

    print(f"\n{'='*60}")
    print(f"Creating: {name}")
    print(f"Price: ${price} | File: {Path(file_path).name}")
    print(f"{'='*60}")

    result = {"name": name, "success": False, "product_id": None, "url": None}

    if not Path(file_path).exists():
        print(f"  ❌ File not found: {file_path}")
        return result

    # Navigate to new product page
    await page.goto("https://gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    await ss(page, f"{slug}_01_new.png")

    # Fill product name
    try:
        name_field = page.locator('input[placeholder*="Name"], input[name="name"], input[placeholder*="name"]').first
        if await name_field.count() == 0:
            name_field = page.locator('input[type="text"]').first
        await name_field.click()
        await name_field.fill(name)
        print(f"  ✓ Name filled")
    except Exception as e:
        print(f"  ❌ Name field error: {e}")
        await dump_page(page, "  ")
        return result

    # Fill price
    try:
        price_field = page.locator('input[placeholder*="price"], input[placeholder*="Price"], input[name="price"], [data-testid*="price"] input').first
        if await price_field.count() == 0:
            price_field = page.locator('input[placeholder*="$"], input[placeholder*="0.00"]').first
        if await price_field.count() > 0:
            await price_field.click()
            await price_field.triple_click()
            await price_field.fill(price)
            print(f"  ✓ Price filled: ${price}")
        else:
            print(f"  ⚠️ Price field not found, will set later")
    except Exception as e:
        print(f"  ⚠️ Price field: {e}")

    await ss(page, f"{slug}_02_filled.png")

    # Click Save / Next
    try:
        next_btn = page.locator('button:has-text("Save and continue"), button:has-text("Next"), button:has-text("Create")').first
        if await next_btn.count() > 0 and await next_btn.is_visible():
            await next_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            print(f"  ✓ Advanced to next step")
    except Exception as e:
        print(f"  ⚠️ Next button: {e}")

    # Get product ID from URL
    cur_url = page.url
    product_id = None
    if "/products/" in cur_url:
        parts = cur_url.split("/products/")
        if len(parts) > 1:
            product_id = parts[1].split("/")[0]
            print(f"  ✓ Product ID: {product_id}")
            result["product_id"] = product_id

    await ss(page, f"{slug}_03_step2.png")

    # Navigate through content/description tab
    for tab_url in [
        f"https://gumroad.com/products/{product_id}/edit" if product_id else None,
    ]:
        if not tab_url:
            continue
        try:
            await page.goto(tab_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(1500)
        except:
            pass

    # Fill description
    try:
        desc_field = page.locator('textarea[name="description"], [contenteditable="true"], .ProseMirror').first
        if await desc_field.count() > 0:
            await desc_field.click()
            await desc_field.fill(desc[:2000])  # Gumroad truncates
            print(f"  ✓ Description filled ({len(desc[:2000])} chars)")
    except Exception as e:
        print(f"  ⚠️ Description field: {e}")

    # Upload file — navigate to content tab
    if product_id:
        try:
            content_url = f"https://gumroad.com/products/{product_id}/edit/content"
            await page.goto(content_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            await ss(page, f"{slug}_04_content.png")

            # Look for file upload input
            file_input = page.locator('input[type="file"]').first
            if await file_input.count() > 0:
                await file_input.set_input_files(file_path)
                print(f"  ✓ File upload initiated: {Path(file_path).name}")
                await page.wait_for_timeout(8000)  # Wait for upload
                await ss(page, f"{slug}_05_uploaded.png")

                # Check upload status
                body = await page.locator("body").inner_text()
                if Path(file_path).name in body or "uploaded" in body.lower() or "download" in body.lower():
                    print(f"  ✓ File uploaded successfully")
                else:
                    print(f"  ⚠️ Upload status unclear")
            else:
                print(f"  ⚠️ File upload input not found")
                await dump_page(page, "  ")
        except Exception as e:
            print(f"  ⚠️ File upload: {e}")

    # Save content tab
    try:
        save_btn = page.locator('button:has-text("Save and continue"), button:has-text("Save")').first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            await save_btn.click()
            await page.wait_for_timeout(3000)
            print(f"  ✓ Content saved")
    except:
        pass

    # Navigate to publish
    if product_id:
        try:
            # Walk through wizard to publish
            for attempt in range(8):
                cur_url = page.url
                body = await page.locator("body").inner_text()

                if "Unpublish" in body:
                    print(f"  ✅ PUBLISHED!")
                    result["success"] = True
                    result["url"] = f"https://gumroad.com/products/{product_id}/edit"
                    break

                # Try publish button
                pub_btn = page.locator('button:has-text("Publish")').first
                if await pub_btn.count() > 0 and await pub_btn.is_visible():
                    print(f"  Clicking Publish (attempt {attempt+1})...")
                    await pub_btn.click()
                    await page.wait_for_timeout(5000)
                    await ss(page, f"{slug}_06_after_publish_{attempt}.png")
                    body2 = await page.locator("body").inner_text()
                    if "Unpublish" in body2:
                        print(f"  ✅ PUBLISHED!")
                        result["success"] = True
                        result["url"] = f"https://gumroad.com/products/{product_id}/edit"
                    break

                # Advance wizard
                save_cont = page.locator('button:has-text("Save and continue")').first
                if await save_cont.count() > 0 and await save_cont.is_visible():
                    await save_cont.click()
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    await page.wait_for_timeout(2000)
                else:
                    # Manual navigation
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
        except Exception as e:
            print(f"  ❌ Publish error: {e}")

    await ss(page, f"{slug}_final.png")
    return result


async def main():
    vault = SessionVault()
    results = []

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("🚀 Publishing AI Operator Products to Gumroad")

        # Verify login
        await page.goto("https://gumroad.com/products", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        if "login" in page.url or "sign" in page.url:
            print("❌ Not logged in to Gumroad!")
            return
        print(f"✓ Logged in. Proceeding to publish 3 products...")

        for product in PRODUCTS:
            r = await create_product(page, product)
            results.append(r)
            await page.wait_for_timeout(2000)  # Brief pause between products

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
                print(f"  Edit URL: https://gumroad.com/products/{r['product_id']}/edit")
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

"""
Pinterest Pin Creation Script — Ten Life Creatives
Creates 3 pins for Gumroad products using saved AgentReach session.

Usage:
    cd /Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach
    .venv/bin/python create_pins.py

Prerequisites:
    - Pinterest session must be harvested: .venv/bin/agentreach harvest pinterest
"""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.vault.store import SessionVault
from agentreach.browser.session import platform_context

PRODUCTS_BASE = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products")

PINS = [
    {
        "title": "Pray Deeper: 52-Week Prayer Journal for Women",
        "description": "Stop going through the motions. Pray Deeper is a 52-week guided prayer journal built for women who want a real, honest conversation with God. Scripture reflection, weekly themes, and space to actually hear back. $6.99 digital download.",
        "link": "https://tenlifejosh.gumroad.com/l/znespo",
        "board": "Prayer Journals",
        "image": PRODUCTS_BASE / "pray-deeper" / "cover-front.png",
    },
    {
        "title": "The Anxiety Unpack: CBT Workbook for Overthinkers",
        "description": "Your brain isn't broken — it's just loud. The Anxiety Unpack is a CBT-based workbook that teaches you to identify thought patterns, interrupt spirals, and build actual calm. Not affirmations. Real tools. $9.99 digital download.",
        "link": "https://tenlifejosh.gumroad.com/l/prjijm",
        "board": "Mental Health & Wellness",
        "image": PRODUCTS_BASE / "anxiety-unpack" / "cover-front.png",
    },
    {
        "title": "Budget Binder 2026 — Monthly Budget Planner Printable",
        "description": "Stop guessing where your money went. The 2026 Budget Binder is a printable monthly planner with income tracking, expense categories, savings goals, and debt payoff sheets. Print once, use all year. $7.99.",
        "link": "https://tenlifejosh.gumroad.com/l/bmjrs",
        "board": "Budget Planners & Finance Printables",
        "image": PRODUCTS_BASE / "budget-binder" / "mockups" / "mockup-1-hero.jpg",
    },
    {
        # TODO: Pray Bold has no Gumroad listing yet — create it at app.gumroad.com/products/new
        # then update the "link" below with the real URL (e.g. https://tenlifejosh.gumroad.com/l/SLUG)
        "title": "Pray Bold: 52-Week Prayer Journal for Men",
        "description": "Most men don't pray because they don't know how to start. Pray Bold is a 52-week guided prayer journal built for men who want a real, honest faith — not a performance. Weekly scripture, daily prompts, space to think and hear. $12.99 digital download.",
        "link": "PLACEHOLDER — add Gumroad URL here before running",
        "board": "Faith Journals & Bible Study",
        "image": PRODUCTS_BASE / "pray-bold" / "cover-front.png",
    },
]


async def take_debug_screenshot(page, name: str):
    path = f"/tmp/pinterest_{name}.png"
    await page.screenshot(path=path)
    print(f"  📸 Screenshot: {path}")


async def find_and_fill(page, selectors: list, value: str, label: str):
    """Try multiple selectors to fill a field."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            count = await el.count()
            if count > 0:
                await el.click()
                await page.wait_for_timeout(300)
                await el.fill(value)
                print(f"  ✓ Filled {label} via: {sel}")
                return True
        except Exception:
            continue
    print(f"  ✗ Could not fill {label} — tried all selectors")
    return False


async def select_or_create_board(page, board_name: str):
    """Select a board or create a new one."""
    board_selectors = [
        '[data-test-id="board-dropdown-select-btn"]',
        '[aria-label="Select a board"]',
        '[placeholder*="board"]',
        '[data-test-id="pin-draft-board"]',
        'button[class*="board"]',
        '[class*="BoardSelector"]',
        '[class*="boardSelector"]',
    ]

    clicked = False
    for sel in board_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.click()
                await page.wait_for_timeout(1500)
                clicked = True
                print(f"  ✓ Board dropdown opened via: {sel}")
                break
        except Exception:
            continue

    if not clicked:
        print("  ✗ Could not open board dropdown")
        return False

    # Search for board
    try:
        search = page.locator('input[placeholder*="Search"]').first
        if await search.count() > 0:
            await search.fill(board_name)
            await page.wait_for_timeout(1000)
    except Exception:
        pass

    # Look for board in dropdown
    board_option = page.locator(f'[title="{board_name}"]').first
    if await board_option.count() == 0:
        board_option = page.locator(f'text="{board_name}"').first
    if await board_option.count() == 0:
        board_option = page.locator(f'[aria-label*="{board_name[:10]}"]').first

    if await board_option.count() > 0:
        await board_option.click()
        print(f"  ✓ Selected board: {board_name}")
        return True
    else:
        print(f"  Board '{board_name}' not found, attempting to create it...")
        create_btn = page.locator('text="Create board"').first
        if await create_btn.count() == 0:
            create_btn = page.locator('[data-test-id="board-create"]').first
        if await create_btn.count() > 0:
            await create_btn.click()
            await page.wait_for_timeout(1000)
            board_name_input = page.locator('input[placeholder*="Name"]').first
            if await board_name_input.count() == 0:
                board_name_input = page.locator('input[id*="boardName"]').first
            if await board_name_input.count() > 0:
                await board_name_input.fill(board_name)
                await page.wait_for_timeout(500)
                create_confirm = page.locator('[data-test-id="board-create-confirm"]').first
                if await create_confirm.count() == 0:
                    create_confirm = page.locator('button[type="submit"]').first
                if await create_confirm.count() > 0:
                    await create_confirm.click()
                    await page.wait_for_timeout(2000)
                    print(f"  ✓ Created new board: {board_name}")
                    return True
        else:
            await page.keyboard.press("Escape")
            print(f"  ⚠ Could not create board '{board_name}', continuing")
            return False


async def create_single_pin(page, pin: dict, pin_num: int):
    """Create a single pin via Pinterest's pin creation tool."""
    print(f"\n--- Creating Pin {pin_num}: {pin['title'][:50]}... ---")

    await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    current_url = page.url
    print(f"  URL after navigation: {current_url}")

    if "login" in current_url or "accounts" in current_url or current_url == "https://www.pinterest.com/":
        # Check if we're on the actual creation tool
        creation_form = await page.locator('[data-test-id="storyboard-upload-input"], [id="pin-draft-title"], input[type="file"]').count()
        if creation_form == 0:
            print("  ✗ Not on pin creation page — session may be invalid")
            return {"success": False, "error": "Session invalid or redirected away from pin creation tool"}

    # Upload image
    image_path = Path(pin["image"])
    if image_path.exists():
        print(f"  Uploading image: {image_path.name}")
        upload_success = False

        upload_zone_selectors = [
            '[data-test-id="storyboard-upload-input"]',
            '[class*="uploadContainer"]',
            '[class*="UploadButton"]',
            '[aria-label*="Upload"]',
            '[aria-label*="upload"]',
            'div[class*="upload"]',
        ]

        for sel in upload_zone_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                        await el.click()
                    fc = await fc_info.value
                    await fc.set_files(str(image_path))
                    await page.wait_for_timeout(4000)
                    upload_success = True
                    print(f"  ✓ Image uploaded via file chooser: {sel}")
                    break
            except Exception:
                continue

        if not upload_success:
            try:
                file_input = page.locator('input[type="file"]').first
                if await file_input.count() > 0:
                    await file_input.set_input_files(str(image_path))
                    await page.wait_for_timeout(4000)
                    upload_success = True
                    print("  ✓ Image uploaded via direct file input")
            except Exception as e:
                print(f"  ✗ File input failed: {e}")

        if not upload_success:
            print("  ⚠ Image upload failed, continuing without image")
    else:
        print(f"  ⚠ Image not found at {image_path}")

    # Fill title
    await find_and_fill(page, [
        '[id="pin-draft-title"]', '[data-test-id="pin-draft-title"]',
        '[placeholder*="Add your title"]', '[placeholder*="title"]',
        'input[name="title"]', '[aria-label*="Title"]',
    ], pin["title"], "title")
    await page.wait_for_timeout(500)

    # Fill description
    await find_and_fill(page, [
        '[id="pin-draft-description"]', '[data-test-id="pin-draft-description"]',
        '[placeholder*="Tell everyone what your Pin is about"]', '[placeholder*="description"]',
        'textarea[name="description"]', '[aria-label*="Description"]', '[aria-label*="description"]',
    ], pin["description"], "description")
    await page.wait_for_timeout(500)

    # Fill destination link
    await find_and_fill(page, [
        '[id="pin-draft-link"]', '[data-test-id="pin-draft-link"]',
        '[placeholder*="Add a destination link"]', '[placeholder*="link"]',
        'input[name="link"]', '[aria-label*="link"]', '[aria-label*="Link"]', '[aria-label*="Destination"]',
    ], pin["link"], "destination link")
    await page.wait_for_timeout(500)

    # Select board
    await select_or_create_board(page, pin["board"])
    await page.wait_for_timeout(1000)

    # Publish
    publish_selectors = [
        '[data-test-id="board-dropdown-save-button"]',
        '[data-test-id="pin-draft-save-button"]',
        '[aria-label*="Publish"]',
        'button:has-text("Publish")',
        'button:has-text("Save")',
    ]

    published = False
    for sel in publish_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_enabled():
                await el.click()
                await page.wait_for_timeout(4000)
                published = True
                print(f"  ✓ Clicked publish via: {sel}")
                break
        except Exception:
            continue

    if not published:
        print("  ✗ Could not find publish button")

    final_url = page.url
    print(f"  Final URL: {final_url}")

    success = "/pin/" in final_url or "pin-creation-success" in final_url
    return {
        "success": success,
        "url": final_url,
        "title": pin["title"],
        "board": pin["board"],
        "published": published,
    }


async def main():
    vault = SessionVault()
    results = []

    print("🎯 Pinterest Pin Creation — Ten Life Creatives")
    print("=" * 60)

    # Check session health first
    from agentreach.vault.health import check_session, SessionStatus
    health = check_session("pinterest", vault)
    print(f"Session health: {health.status}")
    if health.status == SessionStatus.MISSING:
        print("❌ No Pinterest session. Run: .venv/bin/agentreach harvest pinterest")
        return

    async with platform_context("pinterest", vault, headless=True) as (ctx, page):
        print("\n🔐 Verifying Pinterest session...")
        await page.goto("https://www.pinterest.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        if "login" in page.url:
            print("❌ Session expired! Run: .venv/bin/agentreach harvest pinterest")
            return

        # Check _auth cookie
        cookies = await ctx.cookies()
        auth_cookie = next((c for c in cookies if c['name'] == '_auth'), None)
        if auth_cookie and auth_cookie['value'] == '0':
            print("❌ Session invalid (_auth=0). Run: .venv/bin/agentreach harvest pinterest")
            return

        print(f"✅ Session valid — URL: {page.url}")

        for i, pin in enumerate(PINS, 1):
            try:
                result = await create_single_pin(page, pin, i)
                results.append(result)
                print(f"\n  Result: {result}")
            except Exception as e:
                print(f"\n  ❌ Exception creating pin {i}: {e}")
                results.append({"success": False, "error": str(e), "title": pin["title"]})

            if i < len(PINS):
                print(f"\n  ⏳ Waiting 5s before next pin...")
                await page.wait_for_timeout(5000)

    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    for i, r in enumerate(results, 1):
        status = "✅" if r.get("success") else "❌"
        print(f"  {status} Pin {i}: {r.get('title', 'unknown')[:50]}")
        if r.get("url"):
            print(f"     URL: {r['url']}")
        if r.get("error"):
            print(f"     Error: {r['error']}")

    return results


if __name__ == "__main__":
    asyncio.run(main())

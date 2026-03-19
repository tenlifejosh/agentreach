"""
Fix FamliClaw v2 — targeted fixes:
1. Find the correct name input selector and fix the name
2. Check/fix description (deduplicate disclaimer)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault

PRODUCT_ID = "fhlmxiz"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"

CORRECT_NAME = "FamliClaw — Your Family's Complete AI Setup Kit"

DISCLAIMER = "Built on OpenClaw (free, open-source software). FamliClaw is an independently created guide and skill package — not affiliated with or endorsed by the OpenClaw team. Requires ~$10-20/month for AI API access."

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("=== Navigating to FamliClaw edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── DIAGNOSE: Find all inputs ──
        print("\n=== Diagnosing inputs ===")
        inputs = page.locator("input")
        input_count = await inputs.count()
        print(f"Total inputs: {input_count}")
        for i in range(input_count):
            inp = inputs.nth(i)
            try:
                visible = await inp.is_visible()
                inp_type = await inp.get_attribute("type") or "text"
                placeholder = await inp.get_attribute("placeholder") or ""
                value = await inp.input_value()
                name_attr = await inp.get_attribute("name") or ""
                id_attr = await inp.get_attribute("id") or ""
                print(f"  [{i}] type={inp_type} visible={visible} placeholder='{placeholder}' value='{value[:60]}' name='{name_attr}' id='{id_attr}'")
            except Exception as e:
                print(f"  [{i}] error: {e}")

        # ── Check description content ──
        print("\n=== Description content ===")
        desc_area = page.locator('[contenteditable="true"]').first
        desc_count = await desc_area.count()
        print(f"Contenteditable areas: {desc_count}")
        if desc_count > 0:
            current_desc = await desc_area.inner_text()
            print(f"Full description:\n{current_desc}")

        await page.screenshot(path=str(screenshots_dir / "v2_01_initial.png"), full_page=True)

asyncio.run(main())

"""
Fix FamliClaw v3 — final fix:
1. Fix name using correct input selector (id ends with -name)
2. Rewrite description cleanly with disclaimer at the end
3. Save
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

CLEAN_DESCRIPTION = """Everything your family needs to set up a personal AI assistant that never forgets, always helps, and runs 24/7.

FamliClaw includes:
• 56-page setup guide — from zero to running in under 2 hours
• 11 pre-built skill files — Homework Helper, Family Calendar, Chore Tracker, Meal Planner, Home Manager, Family Vault, Smart Reminders, and more
• Permanent memory setup — your AI remembers every preference, milestone, and detail about your family forever
• 4 starter config files — pre-written personality, schedule, memory template, and family profile. Just fill in your names and go.

Your family AI will:
✓ Help kids with homework using the Socratic method (guides them to answers, doesn't just give them)
✓ Send morning briefings to your family group with weather, schedule, and reminders
✓ Plan meals around your dietary restrictions and what's in the fridge
✓ Track chores, send reminders, and celebrate when kids complete them
✓ Store and retrieve family documents — insurance, medical info, school records
✓ Remind you about birthdays, bills, medications, and home maintenance
✓ Adapt to each child's age and learning style

For families who want AI done right — private, powerful, and actually useful.

Built on OpenClaw (free, open-source software). FamliClaw is an independently created guide and skill package — not affiliated with or endorsed by the OpenClaw team. Requires ~$10-20/month for AI API access."""

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("=== Navigating to FamliClaw edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── STEP 1: Fix the product name ──
        print("\n=== Step 1: Fixing product name ===")
        try:
            # Use the id that ends with "-name"
            name_input = page.locator('input[id$="-name"]').first
            count = await name_input.count()
            print(f"Found name input by id$=-name: {count}")
            
            if count == 0:
                # Fallback: first text input
                name_input = page.locator('input[type="text"]').first
                count = await name_input.count()
                print(f"Fallback: first text input: {count}")

            if count > 0:
                current_name = await name_input.input_value()
                print(f"Current name: '{current_name}'")
                await name_input.triple_click()
                await name_input.fill(CORRECT_NAME)
                await page.wait_for_timeout(500)
                new_name = await name_input.input_value()
                print(f"Updated name: '{new_name}'")
            else:
                print("❌ Could not find name input")
        except Exception as e:
            print(f"Error updating name: {e}")

        await page.screenshot(path=str(screenshots_dir / "v3_01_name_fixed.png"), full_page=True)

        # ── STEP 2: Rewrite description cleanly ──
        print("\n=== Step 2: Rewriting description ===")
        try:
            desc_area = page.locator('[contenteditable="true"]').first
            await desc_area.wait_for(timeout=10000)
            
            # Select all and replace
            await desc_area.click()
            await page.keyboard.press("Control+a")
            await page.wait_for_timeout(300)
            
            # Type the clean description
            await page.keyboard.type(CLEAN_DESCRIPTION)
            await page.wait_for_timeout(500)
            
            updated = await desc_area.inner_text()
            print(f"Description length: {len(updated)} chars")
            print(f"Last 200 chars: ...{updated[-200:]}")
        except Exception as e:
            print(f"Error rewriting description: {e}")

        await page.screenshot(path=str(screenshots_dir / "v3_02_desc_fixed.png"), full_page=True)

        # ── STEP 3: Save ──
        print("\n=== Step 3: Saving changes ===")
        try:
            save_btn = page.locator('button:has-text("Save changes")').first
            save_count = await save_btn.count()
            if save_count == 0:
                save_btn = page.locator('button:has-text("Save")').first
                save_count = await save_btn.count()

            if save_count > 0:
                await save_btn.click()
                await page.wait_for_timeout(4000)
                await page.screenshot(path=str(screenshots_dir / "v3_03_saved.png"), full_page=True)
                print("✅ Save clicked")
                
                # Verify by reloading
                await page.reload(wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                # Check name
                name_input2 = page.locator('input[id$="-name"]').first
                if await name_input2.count() > 0:
                    saved_name = await name_input2.input_value()
                    print(f"Saved name: '{saved_name}'")
                    if saved_name == CORRECT_NAME:
                        print("✅ Name confirmed correct!")
                    else:
                        print(f"⚠️  Name mismatch: expected '{CORRECT_NAME}', got '{saved_name}'")
                
                # Check description
                desc2 = page.locator('[contenteditable="true"]').first
                if await desc2.count() > 0:
                    saved_desc = await desc2.inner_text()
                    print(f"Saved description length: {len(saved_desc)} chars")
                    print(f"Last 200 chars: ...{saved_desc[-200:]}")
                    if "not affiliated with or endorsed by" in saved_desc:
                        print("✅ Disclaimer confirmed in description!")
                    else:
                        print("⚠️  Disclaimer not found in description")
            else:
                print("❌ No save button found!")
        except Exception as e:
            print(f"Error saving: {e}")

        print(f"\n🔗 Product URL: https://tenlifejosh.gumroad.com/l/familiclaw")
        print("\nDone!")

asyncio.run(main())

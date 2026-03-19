"""
Fix FamliClaw v4 — final final fix:
1. Fix name using click(click_count=3) + fill
2. Fix description with JS-based clear + type
3. Save and verify
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

CLEAN_DESCRIPTION = "Everything your family needs to set up a personal AI assistant that never forgets, always helps, and runs 24/7.\n\nFamliClaw includes:\n\u2022 56-page setup guide \u2014 from zero to running in under 2 hours\n\u2022 11 pre-built skill files \u2014 Homework Helper, Family Calendar, Chore Tracker, Meal Planner, Home Manager, Family Vault, Smart Reminders, and more\n\u2022 Permanent memory setup \u2014 your AI remembers every preference, milestone, and detail about your family forever\n\u2022 4 starter config files \u2014 pre-written personality, schedule, memory template, and family profile. Just fill in your names and go.\n\nYour family AI will:\n\u2713 Help kids with homework using the Socratic method (guides them to answers, doesn't just give them)\n\u2713 Send morning briefings to your family group with weather, schedule, and reminders\n\u2713 Plan meals around your dietary restrictions and what's in the fridge\n\u2713 Track chores, send reminders, and celebrate when kids complete them\n\u2713 Store and retrieve family documents \u2014 insurance, medical info, school records\n\u2713 Remind you about birthdays, bills, medications, and home maintenance\n\u2713 Adapt to each child's age and learning style\n\nFor families who want AI done right \u2014 private, powerful, and actually useful.\n\nBuilt on OpenClaw (free, open-source software). FamliClaw is an independently created guide and skill package \u2014 not affiliated with or endorsed by the OpenClaw team. Requires ~$10-20/month for AI API access."

screenshots_dir = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/publish_screenshots")
screenshots_dir.mkdir(exist_ok=True)

async def main():
    vault = SessionVault()

    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print("=== Navigating to FamliClaw edit page ===")
        await page.goto(EDIT_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── STEP 1: Fix the product name via JS ──
        print("\n=== Step 1: Fixing product name ===")
        try:
            name_input = page.locator('input[id$="-name"]').first
            current_name = await name_input.input_value()
            print(f"Current name: '{current_name}'")
            
            # Use JS to set the value and trigger React's onChange
            await name_input.click()
            await page.keyboard.press("Meta+a")  # Select all (Mac)
            await page.wait_for_timeout(200)
            await page.keyboard.press("Control+a")  # Also try ctrl+a
            await page.wait_for_timeout(200)
            await name_input.fill(CORRECT_NAME)
            await page.wait_for_timeout(300)
            
            # Trigger change event via JS to ensure React picks it up
            await page.evaluate("""
                const inputs = document.querySelectorAll('input[type="text"]');
                for (const inp of inputs) {
                    if (inp.value && inp.value.includes('FamliClaw')) {
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(inp, arguments[0]);
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        break;
                    }
                }
            """, CORRECT_NAME)
            await page.wait_for_timeout(500)
            
            new_name = await name_input.input_value()
            print(f"Updated name: '{new_name}'")
        except Exception as e:
            print(f"Error updating name: {e}")

        await page.screenshot(path=str(screenshots_dir / "v4_01_name.png"), full_page=True)

        # ── STEP 2: Clear and rewrite description via JS ──
        print("\n=== Step 2: Rewriting description via JS ===")
        try:
            desc_area = page.locator('[contenteditable="true"]').first
            await desc_area.wait_for(timeout=10000)
            await desc_area.click()
            await page.wait_for_timeout(300)
            
            # Clear via JS + set textContent
            await page.evaluate("""
                const el = document.querySelector('[contenteditable="true"]');
                el.focus();
                // Select all text
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            """)
            await page.wait_for_timeout(200)
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(200)
            
            # Check if cleared
            content_after_delete = await desc_area.inner_text()
            print(f"After delete, length: {len(content_after_delete)}")
            
            if len(content_after_delete) > 50:
                # Try keyboard shortcut approach
                await desc_area.click()
                await page.keyboard.press("Control+a")
                await page.wait_for_timeout(200)
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(200)
                content_check = await desc_area.inner_text()
                print(f"After ctrl+a+backspace, length: {len(content_check)}")
            
            # Type new description
            await desc_area.click()
            await page.keyboard.type(CLEAN_DESCRIPTION, delay=2)
            await page.wait_for_timeout(500)
            
            final_desc = await desc_area.inner_text()
            print(f"Final description length: {len(final_desc)}")
            print(f"Last 150 chars: ...{final_desc[-150:]}")
            
        except Exception as e:
            print(f"Error rewriting description: {e}")

        await page.screenshot(path=str(screenshots_dir / "v4_02_desc.png"), full_page=True)

        # ── STEP 3: Save ──
        print("\n=== Step 3: Saving changes ===")
        try:
            save_btn = page.locator('button:has-text("Save changes")').first
            save_count = await save_btn.count()
            if save_count == 0:
                save_btn = page.locator('button:has-text("Save")').first

            await save_btn.click()
            await page.wait_for_timeout(4000)
            print("✅ Save clicked")

            # Reload and verify
            await page.reload(wait_until="networkidle")
            await page.wait_for_timeout(2000)

            name_check = page.locator('input[id$="-name"]').first
            if await name_check.count() > 0:
                saved_name = await name_check.input_value()
                print(f"Saved name: '{saved_name}'")
                print("✅ Name correct!" if saved_name == CORRECT_NAME else f"⚠️  Name wrong: '{saved_name}'")

            desc_check = page.locator('[contenteditable="true"]').first
            if await desc_check.count() > 0:
                saved_desc = await desc_check.inner_text()
                print(f"Saved desc length: {len(saved_desc)}")
                has_disclaimer = "not affiliated with or endorsed by" in saved_desc
                print("✅ Disclaimer present!" if has_disclaimer else "⚠️  Disclaimer missing")
                print(f"Last 200 chars: ...{saved_desc[-200:]}")

        except Exception as e:
            print(f"Error saving: {e}")

        print(f"\n🔗 https://tenlifejosh.gumroad.com/l/familiclaw")

asyncio.run(main())

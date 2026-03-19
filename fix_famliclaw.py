"""
Fix FamliClaw Gumroad listing:
1. Fix name typo: FamiliClaw → FamliClaw
2. Add disclaimer to description
3. Upload corrected ZIP file
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.browser.session import platform_context
from agentreach.vault.store import SessionVault

PRODUCT_ID = "fhlmxiz"
EDIT_URL = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
ZIP_FILE = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/famliclaw-package.zip"

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
        await page.screenshot(path=str(screenshots_dir / "fix_01_initial.png"), full_page=True)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # ── STEP 1: Fix the product name ──
        print("\n=== Step 1: Fixing product name ===")
        try:
            name_input = page.locator('input[placeholder="Name of product"]').first
            await name_input.wait_for(timeout=10000)
            current_name = await name_input.input_value()
            print(f"Current name: '{current_name}'")

            await name_input.triple_click()
            await name_input.fill(CORRECT_NAME)
            await page.wait_for_timeout(500)
            new_name = await name_input.input_value()
            print(f"Updated name: '{new_name}'")
        except Exception as e:
            print(f"Error updating name: {e}")

        await page.screenshot(path=str(screenshots_dir / "fix_02_name_updated.png"), full_page=True)

        # ── STEP 2: Add disclaimer to description ──
        print("\n=== Step 2: Updating description ===")
        try:
            # Find the contenteditable description area
            desc_area = page.locator('[contenteditable="true"]').first
            await desc_area.wait_for(timeout=10000)
            current_desc = await desc_area.inner_text()
            print(f"Current description length: {len(current_desc)} chars")
            print(f"Description ends with: ...{current_desc[-100:]}")

            # Check if disclaimer already exists
            if "Built on OpenClaw (free, open-source software)" in current_desc and "not affiliated with or endorsed by" in current_desc:
                print("⚠️  Full disclaimer already present, skipping description update")
            else:
                # Remove old partial disclaimer line if present, then add full one
                # Click at the end of the content
                await desc_area.click()
                # Go to end
                await page.keyboard.press("Control+End")
                await page.wait_for_timeout(300)
                
                # Type newline + disclaimer
                await page.keyboard.press("Enter")
                await page.keyboard.type(DISCLAIMER)
                await page.wait_for_timeout(500)
                
                updated_desc = await desc_area.inner_text()
                print(f"Updated description length: {len(updated_desc)} chars")
                print(f"Description now ends with: ...{updated_desc[-200:]}")
        except Exception as e:
            print(f"Error updating description: {e}")

        await page.screenshot(path=str(screenshots_dir / "fix_03_desc_updated.png"), full_page=True)

        # ── STEP 3: Upload corrected ZIP file ──
        print("\n=== Step 3: Uploading corrected ZIP file ===")
        zip_path = Path(ZIP_FILE)
        if not zip_path.exists():
            print(f"❌ ZIP file not found: {ZIP_FILE}")
        else:
            print(f"ZIP file exists: {zip_path.name} ({zip_path.stat().st_size:,} bytes)")
            try:
                # Find the file input
                file_input = page.locator('input[type="file"]').first
                
                # Try to find an upload button to trigger it
                upload_btn = page.locator('button:has-text("Upload"), [class*="upload-button"], label[for*="file"]').first
                upload_count = await upload_btn.count()
                
                if upload_count > 0:
                    print("Found upload button, clicking...")
                    await upload_btn.click()
                    await page.wait_for_timeout(1000)

                # Set the file via file input (works even if input is hidden)
                file_inputs = page.locator('input[type="file"]')
                count = await file_inputs.count()
                print(f"Found {count} file input(s)")
                
                for i in range(count):
                    fi = file_inputs.nth(i)
                    try:
                        await fi.set_input_files(str(zip_path))
                        print(f"✅ File set on input #{i}")
                        break
                    except Exception as e2:
                        print(f"  Input #{i} failed: {e2}")

                # Wait for upload to complete
                print("Waiting for upload to complete...")
                await page.wait_for_timeout(5000)
                
                # Check for upload progress indicators
                for _ in range(24):  # wait up to 2 minutes
                    body = await page.locator("body").inner_text()
                    if "famliclaw-package" in body.lower() or "famliclaw" in body.lower() or "uploading" not in body.lower():
                        print("Upload appears complete")
                        break
                    print("  Still uploading...")
                    await page.wait_for_timeout(5000)
                
                await page.screenshot(path=str(screenshots_dir / "fix_04_after_upload.png"), full_page=True)

            except Exception as e:
                print(f"Error uploading file: {e}")

        # ── STEP 4: Save changes ──
        print("\n=== Step 4: Saving changes ===")
        try:
            save_btn = page.locator('button:has-text("Save changes")').first
            save_count = await save_btn.count()
            if save_count == 0:
                save_btn = page.locator('button:has-text("Save")').first
                save_count = await save_btn.count()
            
            if save_count > 0:
                print("Clicking Save changes...")
                await save_btn.click()
                await page.wait_for_timeout(4000)
                await page.screenshot(path=str(screenshots_dir / "fix_05_after_save.png"), full_page=True)
                print(f"After save URL: {page.url}")
                
                # Check for success indication
                body = await page.locator("body").inner_text()
                if "saved" in body.lower() or "updated" in body.lower():
                    print("✅ Save confirmed!")
                else:
                    print("Save clicked, checking state...")
                    lines = [l.strip() for l in body.split('\n') if l.strip()]
                    for line in lines[:20]:
                        print(f"  {line}")
            else:
                print("❌ No save button found!")
                # List visible buttons
                buttons = page.locator("button")
                btn_count = await buttons.count()
                print(f"Available buttons ({btn_count}):")
                for i in range(min(btn_count, 20)):
                    try:
                        text = await buttons.nth(i).inner_text()
                        visible = await buttons.nth(i).is_visible()
                        if visible and text.strip():
                            print(f"  [{i}] '{text.strip()}'")
                    except:
                        pass
        except Exception as e:
            print(f"Error saving: {e}")

        print(f"\n🔗 Product URL: https://tenlifejosh.gumroad.com/l/familiclaw")
        print(f"🔗 Edit URL: {EDIT_URL}")
        print("\nDone!")

asyncio.run(main())

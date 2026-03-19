"""
Test KDP with aggressive anti-detection to try to bypass headless detection.
Amazon may be blocking headless Chromium via fingerprinting.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.vault.store import SessionVault


async def test_antidetect():
    from playwright.async_api import async_playwright

    vault = SessionVault()
    session_data = vault.load("kdp")
    storage_state = session_data.get("storage_state", {})

    async with async_playwright() as p:
        # Use max anti-detection flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1280,900",
                "--start-maximized",
            ],
        )

        context = await browser.new_context(
            storage_state=storage_state if storage_state.get("cookies") else None,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/Denver",
            has_touch=False,
            java_script_enabled=True,
            accept_downloads=True,
        )

        # Override navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                    {filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format'},
                ],
            });
            // Chrome's real runtime
            window.chrome = {
                runtime: {}
            };
        """)

        page = await context.new_page()

        # Test 1: Bookshelf
        await page.goto("https://kdp.amazon.com/en_US/bookshelf", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        bookshelf_ok = "bookshelf" in page.url
        print(f"Bookshelf: {'✅' if bookshelf_ok else '❌'} {page.url[:80]}")

        if bookshelf_ok:
            # Test 2: New paperback URL
            await page.goto(
                "https://kdp.amazon.com/en_US/title-setup/paperback/new/details",
                wait_until="domcontentloaded",
                timeout=30000
            )
            await page.wait_for_timeout(2000)
            creation_ok = "title-setup" in page.url and "signin" not in page.url
            print(f"Title creation: {'✅' if creation_ok else '❌'} {page.url[:80]}")

            if creation_ok:
                print("🎉 Anti-detection WORKED! Can access title creation.")
            else:
                print("❌ Still blocked by step-up auth.")

                # Try from bookshelf page with referrer
                await page.goto("https://kdp.amazon.com/en_US/bookshelf", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Click Create button
                try:
                    create_btn = page.locator('a:has-text("Create a new title"), button:has-text("Create")').first
                    if await create_btn.count() > 0:
                        print("Clicking Create button...")
                        await create_btn.click()
                        await page.wait_for_timeout(3000)
                        print(f"After click: {page.url[:80]}")
                except Exception as e:
                    print(f"Click error: {e}")

        await browser.close()


asyncio.run(test_antidetect())

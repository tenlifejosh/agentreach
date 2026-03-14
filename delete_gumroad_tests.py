"""
Delete test products from Gumroad.
- "Test Upload Debug" (browser-based, might not appear in API)
- "Test Product Delete Me" (API + browser)
"""
import asyncio
import httpx
from src.agentreach.vault.store import SessionVault
from src.agentreach.browser.session import platform_context


async def delete_via_api(access_token: str, product_id: str, product_name: str) -> bool:
    """Delete a product via Gumroad API."""
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://api.gumroad.com/v2/products/{product_id}",
            params={"access_token": access_token},
            timeout=15,
        )
        print(f"API delete '{product_name}': {resp.status_code} — {resp.text[:200]}")
        return resp.status_code == 200


async def delete_via_browser(product_name: str) -> bool:
    """Delete a product via Gumroad web UI."""
    vault = SessionVault()
    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print(f"Navigating to Gumroad products page...")
        await page.goto("https://gumroad.com/products", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        print(f"Current URL: {page.url}")
        content = await page.content()
        
        # Take screenshot for debugging
        await page.screenshot(path="/tmp/gumroad_products.png")
        
        # Check if we're logged in
        if "login" in page.url or "sign_in" in page.url:
            print("ERROR: Not logged in!")
            return False
        
        # Look for all product links/items on the page
        # Gumroad product list items
        print(f"Looking for product: '{product_name}'")
        
        # Try to find the product by text
        product_found = False
        
        # Method 1: Look for product name in the page content
        if product_name in content:
            print(f"Found '{product_name}' in page content")
            product_found = True
        else:
            print(f"'{product_name}' NOT found in page content")
            # Show page title / URL
            print(f"Page title: {await page.title()}")
            print(f"Page URL: {page.url}")
            return False
        
        # Try to click settings/edit for this product
        # Gumroad shows a ... menu or settings icon per product
        try:
            # Find the product row/card containing the name
            product_locator = page.locator(f'text="{product_name}"').first
            await product_locator.wait_for(timeout=5000)
            
            # Look for a nearby settings/more options button
            # Try to find kebab menu or settings icon near this element
            parent = product_locator.locator('xpath=ancestor::*[contains(@class, "product") or contains(@class, "row")][1]')
            
            # Click the "..." or settings button
            settings_btn = parent.locator('[aria-label*="setting"], [aria-label*="more"], button:has-text("..."), [class*="menu"]').first
            try:
                await settings_btn.click(timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                # Try right-clicking on the product
                await product_locator.click(button="right")
                await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Couldn't find settings button: {e}")
        
        # Try to navigate directly to delete
        # In Gumroad, product edit URL is /products/{id}/edit
        # Delete is typically in the edit page under "Danger zone"
        # Let's try the edit page approach
        
        # Find product ID from href links on the page
        links = await page.eval_on_selector_all('a[href*="/products/"]', 
            'els => els.map(el => ({href: el.href, text: el.textContent.trim()}))')
        
        print(f"Found {len(links)} product links")
        for link in links[:20]:
            print(f"  {link}")
        
        return False


async def delete_product_via_browser_edit(product_api_id: str = None, product_name: str = None) -> bool:
    """Navigate to product edit page and use the delete button there."""
    vault = SessionVault()
    async with platform_context("gumroad", vault, headless=True) as (ctx, page):
        print(f"Loading products page...")
        await page.goto("https://gumroad.com/products", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        if "login" in page.url:
            print("ERROR: Session expired!")
            return False
        
        print(f"URL: {page.url}")
        
        # Dump all text links on the page
        links = await page.eval_on_selector_all('a', 
            'els => els.map(el => ({href: el.href, text: el.textContent.trim().substring(0, 80)}))')
        
        # Find edit links for products
        product_edit_links = [l for l in links if '/products/' in l.get('href', '') and '/edit' in l.get('href', '')]
        print(f"Product edit links: {len(product_edit_links)}")
        for link in product_edit_links:
            print(f"  {link}")
        
        return False


async def main():
    vault = SessionVault()
    session = vault.load("gumroad")
    access_token = session.get("access_token") if session else None
    
    print(f"Access token available: {bool(access_token)}")
    
    # First, delete "Test Product Delete Me" via API
    if access_token:
        test_delete_id = "m7OYT3b3Wm7m3QoC-DgZbg=="
        result = await delete_via_api(access_token, test_delete_id, "Test Product Delete Me")
        if result:
            print("✅ 'Test Product Delete Me' deleted via API")
        else:
            print("❌ Failed to delete 'Test Product Delete Me' via API")
    
    # Now use browser to find and delete "Test Upload Debug"
    print("\n--- Browser approach for 'Test Upload Debug' ---")
    await delete_product_via_browser_edit()


asyncio.run(main())

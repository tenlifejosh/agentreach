"""
Upload Scripture Memory Cards to Gumroad + check sales.
"""
import asyncio
import sys
import os

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.drivers.gumroad import GumroadDriver, GumroadProduct
from agentreach.vault.store import SessionVault

PRODUCT = GumroadProduct(
    name="Scripture Memory Cards — 52 Verses Every Believer Should Know",
    description="52 printable scripture memory cards — cut out and carry with you. Each card has the full NIV verse on the front, a memory prompt and reflection question on the back. 8 categories: Faith, Prayer, Trust, Identity, Peace, Strength, Love, Purpose. Print once, use forever.",
    price_cents=499,
    file_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/scripture-memory-cards/scripture-memory-cards.pdf",
)

async def main():
    vault = SessionVault()
    driver = GumroadDriver(vault=vault)

    # Check session health
    print("Checking Gumroad browser session...")
    valid = await driver.verify_browser_session()
    print(f"Browser session valid: {valid}")

    # Check API token and sales
    print("\nChecking sales via API...")
    try:
        sales_data = driver.check_sales()
        sales = sales_data.get("sales", [])
        print(f"Total recent sales: {len(sales)}")
        for s in sales:
            print(f"  - {s.get('product_name')} | ${s.get('price')/100:.2f} | {s.get('created_at', '')[:10]}")

        # Also get products to check specific ones
        products = await driver.list_products()
        print(f"\nAll products ({len(products)}):")
        for p in products:
            print(f"  - [{p.get('short_url','')}] {p.get('name','')} | published: {p.get('published', False)}")
    except Exception as e:
        print(f"API check failed: {e}")

    # Upload the product
    print("\nUploading Scripture Memory Cards to Gumroad...")
    result = await driver.create_product(PRODUCT)
    print(f"\nResult: success={result.success}")
    print(f"URL: {result.url}")
    print(f"Product ID: {result.product_id}")
    if result.error:
        print(f"Error: {result.error}")
    if result.message:
        print(f"Message: {result.message}")

asyncio.run(main())

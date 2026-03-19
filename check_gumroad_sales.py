"""
Check Gumroad sales and products.
"""
import asyncio
import sys

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.drivers.gumroad import GumroadDriver
from agentreach.vault.store import SessionVault

async def main():
    vault = SessionVault()
    driver = GumroadDriver(vault=vault)

    # Check API token and sales
    print("Checking sales via API...")
    try:
        sales_data = await driver.get_sales()
        sales = sales_data.get("sales", [])
        print(f"Total recent sales: {len(sales)}")
        for s in sales:
            print(f"  - {s.get('product_name')} | ${float(s.get('price', 0))/100:.2f} | {s.get('created_at', '')[:10]}")
    except Exception as e:
        print(f"Sales API failed: {e}")

    # List all products
    try:
        products = await driver.list_products()
        print(f"\nAll products ({len(products)}):")
        for p in products:
            url = p.get('short_url', '') or p.get('url', '') or p.get('id', '')
            name = p.get('name', '')
            published = p.get('published', False)
            revenue = p.get('revenue', 0)
            sales_count = p.get('sales_count', 0)
            print(f"  [{url}] {name} | published={published} | sales={sales_count} | revenue=${float(revenue)/100:.2f}")
    except Exception as e:
        print(f"Products list failed: {e}")

asyncio.run(main())

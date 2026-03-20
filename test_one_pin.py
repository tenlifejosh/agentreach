"""
Test posting a single pin to verify the flow works.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agentreach.drivers.pinterest import PinterestDriver, PinterestPin

async def main():
    driver = PinterestDriver()
    
    pin = PinterestPin(
        title="Budget Binder 2026 — Monthly Financial Planner Printable",
        description="Stop guessing where your money went. The 2026 Budget Binder is a printable monthly planner with income tracking, expense categories, savings goals, and debt payoff sheets. Print once, use all year. $7.99 instant download. #budgetplanner #budgetbinder #printable #personalfinance #savingmoney",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-1-hero.jpg",
        link="https://tenlifejosh.gumroad.com/l/bmjrs",
        board_name="Budget Planners & Finance Printables",
    )
    
    print(f"Posting pin: {pin.title}")
    print(f"Board: {pin.board_name}")
    
    result = await driver.create_pin(pin)
    print(f"\nResult: success={result.success}")
    print(f"Message: {result.message}")
    print(f"URL: {result.url}")
    print(f"Error: {result.error}")

asyncio.run(main())

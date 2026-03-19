"""
Publish FamiliClaw — Your Family's Complete AI Setup Kit to Gumroad.
Price: $47
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/src")

from agentreach.drivers.gumroad import GumroadDriver, GumroadProduct
from agentreach.vault.store import SessionVault

FILE_PATH = "/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/familiclaw-package.zip"

DESCRIPTION = """Everything your family needs to set up a personal AI assistant that never forgets, always helps, and runs 24/7.

FamiliClaw includes:
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

Built on OpenClaw (free, open-source). Requires ~$10-20/month for AI API access.

For families who want AI done right — private, powerful, and actually useful."""

async def main():
    vault = SessionVault()
    driver = GumroadDriver(vault=vault)

    product = GumroadProduct(
        name="FamiliClaw — Your Family's Complete AI Setup Kit",
        description=DESCRIPTION,
        price_cents=4700,  # $47.00
        custom_url="familiclaw",
        file_path=FILE_PATH,
    )

    print(f"Publishing: {product.name}")
    print(f"Price: ${product.price_cents / 100}")
    print(f"File: {product.file_path}")
    print()

    result = await driver.create_product(product)

    print(f"\n=== RESULT ===")
    print(f"Success: {result.success}")
    print(f"Platform: {result.platform}")
    print(f"Product ID: {result.product_id}")
    print(f"URL: {result.url}")
    if result.message:
        print(f"Message: {result.message}")
    if result.error:
        print(f"Error: {result.error}")

asyncio.run(main())

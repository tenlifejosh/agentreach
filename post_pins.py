"""
Post all Ten Life Creatives Gumroad products to Pinterest.
Run from: /Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agentreach.drivers.pinterest import PinterestDriver, PinterestPin

FAMLICLAW_IMAGE = "/Users/oliverhutchins1/.openclaw/media/tool-image-generation/famliclaw-cover---cbce4eae-b216-400c-86c2-c41fe322b0c3.png"

PINS = [
    PinterestPin(
        title="Budget Binder 2026 — Monthly Financial Planner Printable",
        description="Stop guessing where your money went. The 2026 Budget Binder is a printable monthly planner with income tracking, expense categories, savings goals, and debt payoff sheets. Print once, use all year. $7.99 instant download. #budgetplanner #budgetbinder #printable #personalfinance #savingmoney",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-1-hero.jpg",
        link="https://tenlifejosh.gumroad.com/l/bmjrs",
        board_name="Budget Planners & Finance Printables",
    ),
    PinterestPin(
        title="Pray Deeper: 52-Week Prayer Journal for Women",
        description="Stop going through the motions. Pray Deeper is a 52-week guided prayer journal for women who want a real conversation with God. Scripture, daily prompts, space to hear back. $6.99 instant download. #prayerjournal #faithjournal #christianwomen #biblejournal #devotional",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-deeper/cover-front.png",
        link="https://tenlifejosh.gumroad.com/l/znespo",
        board_name="Prayer Journals & Faith Planners",
    ),
    PinterestPin(
        title="The Anxiety Unpack — CBT Workbook for Overthinkers",
        description="Real CBT tools, not affirmations. Identify thought patterns, interrupt anxiety spirals, build actual calm. $9.99 instant download. #anxietyhelp #cbtworkbook #mentalhealth #anxietyrelief #selfhelpworkbook",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/anxiety-unpack/cover-front.png",
        link="https://tenlifejosh.gumroad.com/l/prjijm",
        board_name="Mental Health & Wellness",
    ),
    PinterestPin(
        title="Scripture Memory Cards — 52 Printable Bible Verse Cards",
        description="52 printable flash cards with NIV Bible verses. Front: full verse. Back: memory prompt and reflection question. Print and carry. $4.99 instant download. #bibleverses #scripturememory #christianprintable #bibleverse #faithprintable",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/scripture-memory-cards/cover-gumroad.png",
        link="https://tenlifejosh.gumroad.com/l/ckdqjk",
        board_name="Bible Study & Scripture",
    ),
    PinterestPin(
        title="FamliClaw — Set Up Your Own Family AI Assistant",
        description="Everything your family needs to set up a personal AI that never forgets, helps with homework, plans meals, tracks chores, and runs 24/7. Complete setup guide + 11 skill files. $47. #familytech #aitools #parenting #homeschool #familyorganization",
        image_path=FAMLICLAW_IMAGE,
        link="https://tenlifejosh.gumroad.com/l/fhlmxiz",
        board_name="AI Tools & Technology",
    ),
]


async def main():
    driver = PinterestDriver()

    # Verify session
    ok = await driver.verify_session()
    print(f"Session valid: {ok}")
    if not ok:
        print("ERROR: Pinterest session is not valid. Re-harvest needed.")
        return

    results = []
    for i, pin in enumerate(PINS, 1):
        print(f"\n[{i}/{len(PINS)}] Posting: {pin.title}")
        print(f"  Board: {pin.board_name}")
        print(f"  Image: {pin.image_path}")

        # Check image exists
        if not Path(pin.image_path).exists():
            print(f"  WARNING: Image not found, skipping: {pin.image_path}")
            results.append({"pin": pin.title, "success": False, "error": "Image not found"})
            continue

        result = await driver.create_pin(pin)
        if result.success:
            print(f"  ✓ SUCCESS: {result.message}")
            print(f"  URL: {result.url}")
        else:
            print(f"  ✗ FAILED: {result.error}")

        results.append({
            "pin": pin.title,
            "success": result.success,
            "url": getattr(result, "url", None),
            "error": getattr(result, "error", None),
            "message": getattr(result, "message", None),
        })

        # Brief pause between pins
        if i < len(PINS):
            print("  Waiting 5s before next pin...")
            await asyncio.sleep(5)

    print("\n=== RESULTS SUMMARY ===")
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"{status} {r['pin']}")
        if r.get("url"):
            print(f"   URL: {r['url']}")
        if r.get("error"):
            print(f"   Error: {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())

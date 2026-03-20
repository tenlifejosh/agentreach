"""
Post batch 2 of Ten Life Creatives pins to Pinterest — multiple angles per product.
Run from: /Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach/
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agentreach.drivers.pinterest import PinterestDriver, PinterestPin

FAMLICLAW_IMAGE = "/Users/oliverhutchins1/.openclaw/media/tool-image-generation/famliclaw-cover---cbce4eae-b216-400c-86c2-c41fe322b0c3.png"

PINS = [
    # Budget Binder — 3 more angles
    PinterestPin(
        title="How I Finally Stopped Overspending — Budget Binder 2026",
        description="I used to wonder where all my money went every month. Then I started the Budget Binder system. Monthly sheets, weekly trackers, savings goals — everything in one printable. $7.99. #budgetbinder #personalfinance #savingmoney #budgeting #financialplanning",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-2-spread.jpg",
        link="https://gumroad.com/l/bmjrs",
        board_name="Budget Planners & Finance Printables",
    ),
    PinterestPin(
        title="The Only Budget Printable You Need in 2026",
        description="12 monthly budget sheets + weekly expense tracker + debt payoff planner + savings goals tracker. Print once, use all year. $7.99 instant download. #budgetplanner #printable #financialgoals #debtfree #moneymanagement",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-3-lifestyle.jpg",
        link="https://gumroad.com/l/bmjrs",
        board_name="Budget Planners & Finance Printables",
    ),
    PinterestPin(
        title="Budget Binder 2026 — Printable Monthly Planner for Every Income",
        description="Works for any income. Track what comes in, what goes out, and where you want to go. The Budget Binder 2026 makes it simple. $7.99 printable PDF. #frugalliving #budgeting #moneytips #financialfreedom #personalfinance",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/budget-binder/mockups/mockup-4-features.jpg",
        link="https://gumroad.com/l/bmjrs",
        board_name="Frugal Living & Money Tips",
    ),
    # Pray Deeper — 2 more angles
    PinterestPin(
        title="52 Weeks of Going Deeper With God — Prayer Journal for Women",
        description="Not a to-do list for God. A real conversation. Pray Deeper gives you 52 weeks of scripture, prompts, and space to hear back. $6.99. #christianwomen #faithjournal #prayer #devotional #biblejournal",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-deeper/cover-front.png",
        link="https://gumroad.com/l/znespo",
        board_name="Christian Women & Faith",
    ),
    PinterestPin(
        title="What If You Actually Heard Back When You Prayed?",
        description="Pray Deeper is built for women who want more than a prayer habit — they want a real relationship with God. 52 weeks. Scripture + prompts + reflection. $6.99. #prayerlife #christianfaith #journaling #womenoffaith #devotional",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-deeper/cover-front.png",
        link="https://gumroad.com/l/znespo",
        board_name="Prayer Journals & Faith Planners",
    ),
    # Anxiety Unpack — 2 more angles
    PinterestPin(
        title="CBT Workbook for Anxiety — Real Tools, Not Affirmations",
        description="Cognitive Behavioral Therapy exercises you can do at home. Thought records, distortion identification, exposure hierarchies. The Anxiety Unpack workbook. $9.99. #anxiety #mentalhealth #cbt #anxietyrelief #therapytools",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/anxiety-unpack/cover-front.png",
        link="https://gumroad.com/l/prjijm",
        board_name="Anxiety & Mental Health Resources",
    ),
    PinterestPin(
        title="Stop the Anxiety Loop — CBT Workbook That Actually Works",
        description="Identify the thought. Name the distortion. Break the pattern. The Anxiety Unpack gives you the CBT framework your brain needs. $9.99 instant download. #overthinker #anxietytips #cognitivebehavioraltherapy #mentalwellness #selfhelp",
        image_path="/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/anxiety-unpack/cover-front.png",
        link="https://gumroad.com/l/prjijm",
        board_name="Mental Health & Wellness",
    ),
    # Reddit Master — 2 more angles
    PinterestPin(
        title="How to Use Reddit for Marketing Without Getting Banned — 2026 Guide",
        description="Reddit appears in 97.5% of product review searches. This 734-line playbook covers warm-up protocols, subreddit guides, promotion strategy, and daily routine. $17. #redditmarketing #contentmarketing #digitalmarketing #growthhacking #socialmedia",
        image_path="/Users/oliverhutchins1/.openclaw/media/tool-image-generation/reddit-master-cover---1827edb7-0a37-45a6-bef8-c401cbc9b2ce.png",
        link="https://gumroad.com/l/vwuweq",
        board_name="Marketing & Business Growth",
    ),
    PinterestPin(
        title="The Reddit Marketing Playbook No One Talks About",
        description="90-day warm-up protocol. Subreddit field guides. How to mention products without getting banned. Built for AI agents and humans. $17 instant download. #reddit #marketing #organictraffic #contentcreator #digitalmarketing",
        image_path="/Users/oliverhutchins1/.openclaw/media/tool-image-generation/reddit-master-cover---1827edb7-0a37-45a6-bef8-c401cbc9b2ce.png",
        link="https://gumroad.com/l/vwuweq",
        board_name="Marketing & Business Growth",
    ),
    # FamliClaw — 1 more angle
    PinterestPin(
        title="Set Up Your Own Family AI in Under 2 Hours",
        description="FamliClaw turns OpenClaw into a personalized family assistant. Homework help, meal planning, chore tracking, family vault, and permanent memory. 56-page guide + 11 skill files. $47. #familytech #aitools #smartfamily #parenting #homeschool",
        image_path=FAMLICLAW_IMAGE,
        link="https://gumroad.com/l/fhlmxiz",
        board_name="Smart Home & Family Tech",
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

        # Check image exists (skip PDFs — driver needs image files)
        img_path = Path(pin.image_path)
        if not img_path.exists():
            print(f"  WARNING: Image not found, skipping: {pin.image_path}")
            results.append({"pin": pin.title, "success": False, "error": "Image not found"})
            continue

        if img_path.suffix.lower() == ".pdf":
            print(f"  WARNING: PDF not supported as pin image, skipping: {pin.image_path}")
            results.append({"pin": pin.title, "success": False, "error": "PDF not supported as pin image"})
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

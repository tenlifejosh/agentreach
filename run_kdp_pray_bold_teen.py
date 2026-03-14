"""
KDP End-to-End Test: Pray Bold — Teen Edition
Runs the full KDP driver pipeline: details → content → pricing → publish
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentreach.drivers.kdp import KDPDriver, KDPBookDetails

MANUSCRIPT = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/interior.pdf")
COVER = Path("/Users/oliverhutchins1/.openclaw/workspace-main/projects/revenue/products/pray-bold-teen/cover-full-wrap.pdf")

details = KDPBookDetails(
    title="Pray Bold: Teen Edition",
    subtitle="A 52-Week Prayer Journal for Teenagers",
    author="Joshua Noreen",
    description=(
        "Built for teenagers who want to grow in faith. "
        "52 weeks of guided prayer prompts, scripture reflection, and space to hear from God"
        "—designed for the pace and questions of teenage life."
    ),
    keywords=[
        "teen prayer journal",
        "christian teen journal",
        "bible journal for teenagers",
        "faith journal teen",
        "prayer book for teens",
        "christian gifts for teens",
        "teen devotional journal",
    ],
    categories=["Religion & Spirituality > Christian Books & Bibles > Christian Living"],
    price_usd=12.99,
)


async def main():
    print("=" * 60)
    print("KDP End-to-End Test: Pray Bold — Teen Edition")
    print("=" * 60)
    print(f"Manuscript: {MANUSCRIPT} (exists: {MANUSCRIPT.exists()})")
    print(f"Cover: {COVER} (exists: {COVER.exists()})")
    print()

    driver = KDPDriver()

    print("Verifying KDP session...")
    session_ok = await driver.verify_session()
    print(f"Session valid: {session_ok}")
    if not session_ok:
        print("ERROR: KDP session is not valid. Please re-harvest.")
        return

    print("\nStarting paperback creation...")
    result = await driver.create_paperback(details, MANUSCRIPT, COVER)

    print("\n" + "=" * 60)
    print("RESULT:")
    print(f"  Success:    {result.success}")
    print(f"  Platform:   {result.platform}")
    print(f"  Product ID: {result.product_id}")
    print(f"  URL:        {result.url}")
    print(f"  Message:    {result.message}")
    if result.error:
        print(f"  ERROR:      {result.error}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result and result.success else 1)

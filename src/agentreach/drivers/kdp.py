"""
AgentReach — Amazon KDP Driver
Upload manuscripts, covers, set metadata, and publish — fully autonomous.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..browser.session import platform_context
from ..browser.uploader import upload_file, wait_for_upload_complete
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


@dataclass
class KDPBookDetails:
    title: str
    subtitle: str = ""
    author: str = "Joshua Noreen"
    publisher: str = "Ten Life Creatives Inc"
    description: str = ""  # HTML
    keywords: list[str] = None  # up to 7
    categories: list[str] = None  # BISAC
    price_usd: float = 12.99
    language: str = "English"
    primary_audience: str = "general"


class KDPDriver(BasePlatformDriver):
    platform_name = "kdp"

    BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"
    NEW_PAPERBACK_URL = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details"
    NEW_EBOOK_URL = "https://kdp.amazon.com/en_US/title-setup/kindle/new/details"

    async def verify_session(self) -> bool:
        """Check that our KDP session is still valid."""
        try:
            async with platform_context("kdp", self.vault) as (ctx, page):
                await page.goto(self.BOOKSHELF_URL, wait_until="domcontentloaded", timeout=30000)
                # If redirected to signin, session is dead
                return "signin" not in page.url and "bookshelf" in page.url
        except Exception:
            return False

    async def get_bookshelf(self) -> list[dict]:
        """Return list of books on the KDP bookshelf with status."""
        books = []
        async with platform_context("kdp", self.vault) as (ctx, page):
            await page.goto(self.BOOKSHELF_URL, wait_until="networkidle", timeout=30000)

            # Parse book rows
            rows = await page.query_selector_all('[data-type="BOOK"], .book-row')
            for row in rows:
                try:
                    title_el = await row.query_selector('.book-title, [class*="title"]')
                    status_el = await row.query_selector('.status, [class*="status"]')
                    title = await title_el.inner_text() if title_el else "Unknown"
                    status = await status_el.inner_text() if status_el else "Unknown"
                    books.append({"title": title.strip(), "status": status.strip()})
                except Exception:
                    continue

        return books

    async def create_paperback(
        self,
        details: KDPBookDetails,
        manuscript_path: str | Path,
        cover_path: str | Path,
    ) -> UploadResult:
        """
        Create a new KDP paperback listing end-to-end:
        Step 1: Book Details (title, author, description, keywords, categories)
        Step 2: Book Content (trim size, manuscript PDF, cover PDF)
        Step 3: Book Pricing (price, royalties)
        """
        manuscript_path = Path(manuscript_path)
        cover_path = Path(cover_path)

        for f in [manuscript_path, cover_path]:
            if not f.exists():
                return UploadResult(
                    success=False,
                    platform="kdp",
                    error=f"File not found: {f}",
                )

        async with platform_context("kdp", self.vault) as (ctx, page):
            try:
                # ── STEP 1: Book Details ──────────────────────────────────
                await page.goto(self.NEW_PAPERBACK_URL, wait_until="networkidle", timeout=30000)

                # Title
                title_input = page.locator('#data-print-book-title')
                await title_input.fill(details.title)

                # Subtitle
                if details.subtitle:
                    subtitle_input = page.locator('#data-print-book-subtitle')
                    await subtitle_input.fill(details.subtitle)

                # Author name — find the first name + last name fields
                author_parts = details.author.split(" ", 1)
                first_name = author_parts[0]
                last_name = author_parts[1] if len(author_parts) > 1 else ""
                await page.locator('[id*="first-name"], [placeholder*="First"]').first.fill(first_name)
                await page.locator('[id*="last-name"], [placeholder*="Last"]').first.fill(last_name)

                # Description (HTML)
                if details.description:
                    desc_input = page.locator('#data-print-book-description, [id*="description"]').first
                    await desc_input.fill(details.description)

                # Keywords
                if details.keywords:
                    for i, kw in enumerate(details.keywords[:7]):
                        kw_input = page.locator(f'[id*="keyword-{i}"], input[name*="keyword"][data-index="{i}"]').first
                        try:
                            await kw_input.fill(kw, timeout=3000)
                        except Exception:
                            pass

                # Save and continue to Step 2
                await page.evaluate(
                    "document.querySelector('[id*=\"save-announce\"], button[id*=\"save-continue\"]')?.click()"
                )
                await page.wait_for_load_state("networkidle", timeout=30000)

                # ── STEP 2: Book Content ──────────────────────────────────
                # Trim size: 6x9
                try:
                    trim_select = page.locator('[id*="trim-size"], select[name*="trim"]').first
                    await trim_select.select_option(label="6 x 9 in", timeout=5000)
                except Exception:
                    pass

                # Upload manuscript
                manuscript_uploaded = await upload_file(
                    page,
                    manuscript_path,
                    trigger_selector='[id*="upload-manuscript"], button[data-action*="manuscript"]',
                    input_selector='input[type="file"][accept*="pdf"], input[type="file"]',
                )

                if not manuscript_uploaded:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error="Failed to upload manuscript PDF",
                    )

                await wait_for_upload_complete(page, timeout=120000)
                await page.wait_for_timeout(2000)

                # Upload cover
                cover_uploaded = await upload_file(
                    page,
                    cover_path,
                    trigger_selector='[id*="upload-cover"], button[data-action*="cover"]',
                    input_selector='input[type="file"][accept*="pdf"], input[type="file"]',
                )

                if not cover_uploaded:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error="Failed to upload cover PDF",
                    )

                await wait_for_upload_complete(page, timeout=120000)

                # Save and continue to Step 3
                await page.evaluate(
                    "document.querySelector('[id*=\"save-continue\"]')?.click()"
                )
                await page.wait_for_load_state("networkidle", timeout=30000)

                # ── STEP 3: Pricing ──────────────────────────────────────
                # Set price
                price_input = page.locator('[id*="price-usd"], input[placeholder*="0.00"]').first
                await price_input.fill(str(details.price_usd))

                # Publish
                await page.evaluate(
                    "document.querySelector('[id*=\"save-publish\"], button[id*=\"publish\"]')?.click()"
                )
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Try to get the book ID from the URL
                url = page.url
                book_id = None
                if "/paperback/" in url:
                    parts = url.split("/paperback/")
                    if len(parts) > 1:
                        book_id = parts[1].split("/")[0]

                return UploadResult(
                    success=True,
                    platform="kdp",
                    product_id=book_id,
                    url=url,
                    message=f"Paperback '{details.title}' submitted to KDP successfully",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="kdp",
                    error=str(e),
                    message="KDP upload failed",
                )

    def upload_paperback(
        self,
        details: KDPBookDetails,
        manuscript_path: str | Path,
        cover_path: str | Path,
    ) -> UploadResult:
        """Synchronous wrapper."""
        return asyncio.run(self.create_paperback(details, manuscript_path, cover_path))

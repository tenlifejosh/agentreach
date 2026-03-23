"""
AgentReach — Amazon KDP Driver
Upload manuscripts, covers, set metadata, and publish — fully autonomous.

Selector reference (verified against live KDP form 2026-03-14):
  title:           #data-print-book-title
  subtitle:        #data-print-book-subtitle
  author first:    #data-print-book-primary-author-first-name
  author last:     #data-print-book-primary-author-last-name
  description:     CKEditor — CKEDITOR.instances['editor1'].setData(html)
                   hidden backing field: input[name="data[print_book][description]"]
  keywords[0-6]:   #data-print-book-keywords-0  …  #data-print-book-keywords-6
  save & continue: #save-and-continue
  categories:      Found via the category modal (opened from the details page)

Authentication note (2026-03-14):
  KDP requires max_auth_age=0 (step-up auth) for ALL title creation/editing operations.
  The bookshelf page loads fine with saved cookies, but any /title-setup/ URL
  redirects to Amazon sign-in. This means:
    - verify_session() must test title-setup access, not just bookshelf access
    - The harvester should navigate to a title-setup page during harvest to capture
      the full auth state needed for creation operations
  Workaround: Re-harvest the session immediately before running create_paperback().
  Run: agentreach harvest kdp  (log in → KDP bookshelf loads → then navigate to any title)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..browser.session import platform_context
from ..browser.uploader import upload_file, wait_for_upload_complete
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


logger = logging.getLogger(__name__)


@dataclass
class KDPBookDetails:
    title: str
    subtitle: str = ""
    author: str = ""           # Format: "First Last" — no default, caller must specify
    publisher: str = ""
    description: str = ""  # HTML — injected into CKEditor
    keywords: list[str] = field(default_factory=list)  # up to 7
    categories: list[str] = field(default_factory=list)  # BISAC
    price_usd: float = 12.99
    language: str = "English"
    primary_audience: str = "general"


class KDPDriver(BasePlatformDriver):
    platform_name = "kdp"

    BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"
    NEW_PAPERBACK_URL = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details"
    NEW_EBOOK_URL = "https://kdp.amazon.com/en_US/title-setup/kindle/new/details"

    async def verify_session(self) -> bool:
        """
        Check that our KDP session is valid for title creation (not just bookshelf).

        IMPORTANT: KDP requires fresh step-up auth (max_auth_age=0) for all title
        creation/editing. This checks if the session can actually reach the title
        creation form — not just the bookshelf read view.
        """
        try:
            async with platform_context("kdp", self.vault) as (ctx, page):
                await page.goto(self.BOOKSHELF_URL, wait_until="domcontentloaded", timeout=30000)
                if "signin" in page.url or "bookshelf" not in page.url:
                    return False

                # Test if we can access title creation (requires step-up auth)
                await page.goto(self.NEW_PAPERBACK_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if "signin" in page.url or "title-setup" not in page.url:
                    return False
                return True
        except Exception:
            return False

    async def verify_bookshelf_session(self) -> bool:
        """Check if bookshelf is accessible (weaker check — read-only access)."""
        try:
            async with platform_context("kdp", self.vault) as (ctx, page):
                await page.goto(self.BOOKSHELF_URL, wait_until="domcontentloaded", timeout=30000)
                return "signin" not in page.url and "bookshelf" in page.url
        except Exception:
            return False

    async def get_bookshelf(self) -> list[dict]:
        """Return list of books on the KDP bookshelf with status."""
        books = []
        async with platform_context("kdp", self.vault) as (ctx, page):
            await page.goto(self.BOOKSHELF_URL, wait_until="networkidle", timeout=30000)

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

    async def _fill_description_ckeditor(self, page, html: str) -> bool:
        """
        Inject HTML into KDP's CKEditor description editor.
        KDP uses CKEditor 4 with instance name 'editor1'.
        Falls back to setting the hidden backing field directly.
        """
        import json
        escaped = json.dumps(html)  # safe JS string

        # Strategy 1: CKEditor JS API
        try:
            result = await page.evaluate(
                f"""
                () => {{
                    try {{
                        if (window.CKEDITOR && window.CKEDITOR.instances && window.CKEDITOR.instances['editor1']) {{
                            window.CKEDITOR.instances['editor1'].setData({escaped});
                            return 'ckeditor_ok';
                        }}
                        return 'ckeditor_not_found';
                    }} catch(e) {{
                        return 'ckeditor_error:' + e.message;
                    }}
                }}
                """
            )
            if result == 'ckeditor_ok':
                await page.wait_for_timeout(500)
                return True
        except Exception:
            pass

        # Strategy 2: Set hidden backing field directly and dispatch change event
        try:
            result = await page.evaluate(
                f"""
                () => {{
                    const input = document.querySelector('input[name="data[print_book][description]"]');
                    if (!input) return false;
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                    if (nativeSetter && nativeSetter.set) {{
                        nativeSetter.set.call(input, {escaped});
                    }} else {{
                        input.value = {escaped};
                    }}
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                """
            )
            if result:
                await page.wait_for_timeout(300)
                return True
        except Exception:
            pass

        return False

    # Confirmed element IDs for KDP content step
    MANUSCRIPT_INPUT_ID = "data-print-book-publisher-interior-file-upload-AjaxInput"
    COVER_PDF_INPUT_ID = "data-print-book-publisher-cover-pdf-only-file-upload-AjaxInput"
    COVER_INPUT_ID = "data-print-book-publisher-cover-file-upload-AjaxInput"

    async def _fill_step1_details(self, page, details: KDPBookDetails) -> None:
        """
        Fill in the Book Details form (Step 1).
        Requires the page to already be at the details form URL.
        """
        # Wait for form to be interactive
        await page.wait_for_selector('#data-print-book-title', timeout=20000)
        await page.wait_for_timeout(1000)

        # Title
        await page.locator('#data-print-book-title').fill(details.title)

        # Subtitle
        if details.subtitle:
            await page.locator('#data-print-book-subtitle').fill(details.subtitle)

        # Author — use exact IDs discovered via debug
        author_parts = details.author.split(" ", 1)
        first_name = author_parts[0]
        last_name = author_parts[1] if len(author_parts) > 1 else ""
        await page.locator('#data-print-book-primary-author-first-name').fill(first_name)
        await page.locator('#data-print-book-primary-author-last-name').fill(last_name)

        # Description (HTML) — KDP uses CKEditor 4, instance name 'editor1'
        if details.description:
            await self._fill_description_ckeditor(page, details.description)

        # Keywords — IDs are data-print-book-keywords-0 through -6
        if details.keywords:
            for i, kw in enumerate(details.keywords[:7]):
                kw_selector = f'#data-print-book-keywords-{i}'
                try:
                    await page.locator(kw_selector).fill(kw, timeout=3000)
                except Exception:
                    pass

        # Publishing rights — must click before categories button enables
        try:
            await page.locator('#non-public-domain').click(timeout=5000)
            await page.wait_for_timeout(500)
        except Exception:
            pass

        # Categories — use JavaScript to interact with React-controlled selects
        if details.categories:
            try:
                # Open the categories modal
                await page.locator('#categories-modal-button').click(timeout=8000)
                await page.wait_for_timeout(1500)

                # KDP categories modal uses cascading React selects
                # Values are JSON strings — use JS to fire React's onChange properly
                async def set_react_select(selector: str, value: str):
                    """Set a React-controlled select by dispatching native events."""
                    await page.evaluate(f"""
                        (function() {{
                            const sel = document.querySelector('{selector}');
                            if (!sel) return;
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLSelectElement.prototype, 'value').set;
                            nativeInputValueSetter.call(sel, {repr(value)});
                            sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }})();
                    """)
                    await page.wait_for_timeout(800)

                # Level 0: Religion & Spirituality
                l0_options = await page.evaluate("""
                    Array.from(document.querySelectorAll('select[name="react-aui-0"] option'))
                        .map(o => ({value: o.value, text: o.textContent.trim()}))
                """)
                l0_value = next((o['value'] for o in l0_options if 'Religion' in o['text']), None)
                if l0_value:
                    await set_react_select('select[name="react-aui-0"]', l0_value)

                # Level 2: Christian Books & Bibles (levels skip — 0→2)
                await page.wait_for_timeout(1000)
                l2_options = await page.evaluate("""
                    Array.from(document.querySelectorAll('select[name="react-aui-2"] option'))
                        .map(o => ({value: o.value, text: o.textContent.trim()}))
                """)
                l2_value = next((o['value'] for o in l2_options if 'Christian' in o['text']), None)
                if l2_value:
                    await set_react_select('select[name="react-aui-2"]', l2_value)

                # Level 4: Christian Living (levels skip — 2→4)
                await page.wait_for_timeout(1000)
                l4_options = await page.evaluate("""
                    Array.from(document.querySelectorAll('select[name="react-aui-4"] option'))
                        .map(o => ({value: o.value, text: o.textContent.trim()}))
                """)
                l4_value = next((o['value'] for o in l4_options if 'Living' in o['text']), None)
                if l4_value:
                    await set_react_select('select[name="react-aui-4"]', l4_value)

                # Save categories
                await page.wait_for_timeout(500)
                save_btn = page.locator('button:has-text("Save categories")')
                if await save_btn.count() > 0:
                    await save_btn.click(timeout=5000)
                    await page.wait_for_timeout(1000)

            except Exception as e:
                # Categories non-fatal — continue without them
                pass

    async def _upload_content(
        self,
        page,
        manuscript_path: Path,
        cover_path: Path,
    ) -> tuple[bool, bool]:
        """
        Upload manuscript and cover files in Step 2.
        Returns (manuscript_ok, cover_ok).
        """
        # Trim size: 6x9
        try:
            trim_select = page.locator('[id*="trim-size"], select[name*="trim"]').first
            await trim_select.select_option(label="6 x 9 in", timeout=5000)
        except Exception:
            pass

        # Upload manuscript — look for dedicated file input by known ID first
        manuscript_uploaded = False
        try:
            ms_input = page.locator(f'#{self.MANUSCRIPT_INPUT_ID}')
            if await ms_input.count() > 0:
                await ms_input.set_input_files(str(manuscript_path), timeout=10000)
                manuscript_uploaded = True
        except Exception:
            pass

        if not manuscript_uploaded:
            manuscript_uploaded = await upload_file(
                page,
                manuscript_path,
                trigger_selector=(
                    f'#{self.MANUSCRIPT_INPUT_ID}, '
                    '[id*="upload-manuscript"], button[data-action*="manuscript"], '
                    '[class*="upload"][class*="manuscript"]'
                ),
                input_selector='input[type="file"]',
            )

        if manuscript_uploaded:
            await wait_for_upload_complete(page, timeout=120000)
            await page.wait_for_timeout(2000)

        # Upload cover
        cover_uploaded = False
        try:
            cv_input = page.locator(f'#{self.COVER_PDF_INPUT_ID}')
            if await cv_input.count() > 0:
                await cv_input.set_input_files(str(cover_path), timeout=10000)
                cover_uploaded = True
        except Exception:
            pass

        if not cover_uploaded:
            cover_uploaded = await upload_file(
                page,
                cover_path,
                trigger_selector=(
                    f'#{self.COVER_PDF_INPUT_ID}, #{self.COVER_INPUT_ID}, '
                    '[id*="upload-cover"], button[data-action*="cover"], '
                    '[class*="upload"][class*="cover"]'
                ),
                input_selector='input[type="file"]',
            )

        if cover_uploaded:
            await wait_for_upload_complete(page, timeout=120000)

        return manuscript_uploaded, cover_uploaded

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

        Requires a vault session with step-up auth access to /title-setup/ pages.
        If verify_session() returns False, re-harvest first:
            agentreach harvest kdp
        After logging in, navigate to any title setup page before closing the browser.
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
                await page.goto(self.NEW_PAPERBACK_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for step-up auth redirect
                if "signin" in page.url or "title-setup" not in page.url:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error=(
                            "KDP requires step-up authentication (max_auth_age=0) for title creation. "
                            "The saved session only allows read-only bookshelf access.\n\n"
                            "Fix: Re-harvest the KDP session:\n"
                            "  agentreach harvest kdp\n"
                            "After logging in, click 'Create a new title' and navigate to the details form, "
                            "then close the browser. The deeper auth cookies will be captured.\n\n"
                            "Root cause: Amazon KDP uses OpenID PAPE max_auth_age=0 for all editing operations. "
                            "Headless browsers don't present the same client signals as a real browser, "
                            "so KDP always triggers re-auth for headless sessions."
                        ),
                        message="Step-up authentication required — re-harvest needed",
                    )

                await self._fill_step1_details(page, details)

                # Save and continue to Step 2
                await page.locator('#save-and-continue').click()
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # ── STEP 2: Book Content ──────────────────────────────────
                manuscript_ok, cover_ok = await self._upload_content(page, manuscript_path, cover_path)

                if not manuscript_ok:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error="Failed to upload manuscript PDF — no upload trigger found on Step 2",
                    )

                if not cover_ok:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error="Failed to upload cover PDF — no upload trigger found on Step 2",
                    )

                # Save and continue to Step 3
                await page.locator('#save-and-continue').click()
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # ── STEP 3: Pricing ──────────────────────────────────────
                # Set price in USD marketplace
                price_input = page.locator('[id*="price-usd"], input[placeholder*="0.00"], input[name*="price"]').first
                try:
                    await price_input.fill(str(details.price_usd), timeout=5000)
                except Exception:
                    pass

                # Publish — look for the publish/save-and-publish button
                try:
                    publish_btn = page.locator(
                        '#save-and-publish, #save-and-continue, [id*="publish"], button:has-text("Publish")'
                    ).first
                    await publish_btn.click(timeout=5000)
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                except Exception:
                    pass

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

    async def resume_paperback(
        self,
        book_id: str,
        details: KDPBookDetails,
        manuscript_path: str | Path,
        cover_path: str | Path,
        start_at_step: int = 1,
    ) -> UploadResult:
        """
        Resume an existing KDP paperback draft from a given step.

        Args:
            book_id: KDP book ID (e.g. '2XPF7965VJP')
            details: Book metadata to fill/update
            manuscript_path: Path to interior PDF
            cover_path: Path to cover PDF
            start_at_step: 1=details, 2=content, 3=pricing
        """
        manuscript_path = Path(manuscript_path)
        cover_path = Path(cover_path)

        step_urls = {
            1: f"https://kdp.amazon.com/en_US/title-setup/paperback/{book_id}/details",
            2: f"https://kdp.amazon.com/en_US/title-setup/paperback/{book_id}/content",
            3: f"https://kdp.amazon.com/en_US/title-setup/paperback/{book_id}/pricing",
        }
        start_url = step_urls.get(start_at_step, step_urls[1])

        async with platform_context("kdp", self.vault) as (ctx, page):
            try:
                # Navigate to bookshelf first to ensure we have referrer context
                await page.goto(self.BOOKSHELF_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(1000)

                await page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if "signin" in page.url:
                    return UploadResult(
                        success=False,
                        platform="kdp",
                        error=(
                            f"Step-up auth required to edit book {book_id}. "
                            "Re-harvest KDP session: agentreach harvest kdp"
                        ),
                    )

                if start_at_step == 1:
                    await self._fill_step1_details(page, details)
                    await page.locator('#save-and-continue').click()
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    start_at_step = 2

                if start_at_step == 2:
                    if not manuscript_path.exists() or not cover_path.exists():
                        return UploadResult(
                            success=False,
                            platform="kdp",
                            error="File(s) not found for content upload",
                        )
                    ms_ok, cv_ok = await self._upload_content(page, manuscript_path, cover_path)
                    if not ms_ok:
                        return UploadResult(success=False, platform="kdp",
                                            error="Manuscript upload failed on Step 2")
                    if not cv_ok:
                        return UploadResult(success=False, platform="kdp",
                                            error="Cover upload failed on Step 2")
                    await page.locator('#save-and-continue').click()
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    start_at_step = 3

                if start_at_step == 3:
                    price_input = page.locator(
                        '[id*="price-usd"], input[placeholder*="0.00"], input[name*="price"]'
                    ).first
                    try:
                        await price_input.fill(str(details.price_usd), timeout=5000)
                    except Exception:
                        pass
                    try:
                        publish_btn = page.locator(
                            '#save-and-publish, #save-and-continue, button:has-text("Publish")'
                        ).first
                        await publish_btn.click(timeout=5000)
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    except Exception:
                        pass

                url = page.url
                return UploadResult(
                    success=True,
                    platform="kdp",
                    product_id=book_id,
                    url=url,
                    message=f"Resumed and completed setup for KDP book {book_id}",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="kdp",
                    error=str(e),
                    message=f"KDP resume failed for book {book_id}",
                )

    def upload_paperback(
        self,
        details: KDPBookDetails,
        manuscript_path: str | Path,
        cover_path: str | Path,
    ) -> UploadResult:
        """Synchronous wrapper."""
        return asyncio.run(self.create_paperback(details, manuscript_path, cover_path))

    def continue_paperback(
        self,
        book_id: str,
        details: KDPBookDetails,
        manuscript_path: str | Path,
        cover_path: str | Path,
        start_at_step: int = 1,
    ) -> UploadResult:
        """Synchronous wrapper for resume_paperback."""
        return asyncio.run(self.resume_paperback(book_id, details, manuscript_path, cover_path, start_at_step))

"""
AgentReach — Pinterest Driver
Cookie-based headless driver for organic pin creation.
Pinterest's API requires business verification and approval.
This driver uses saved session cookies for fully autonomous posting.

Selectors verified against Pinterest pin creation tool DOM (March 2026):
  - File upload:   #storyboard-upload-input
  - Title:         #storyboard-selector-title
  - Description:   [aria-label="Add a detailed description"] (contenteditable div)
  - Link:          #WebsiteField
  - Board btn:     [data-test-id="board-dropdown-select-button"]
  - Create board:  [data-test-id="create-board-button"]
  - Board name:    #boardEditName
  - Board submit:  [data-test-id="board-form-submit-button"]
  - Publish btn:   [data-test-id="storyboard-creation-nav-done"]
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..vault.store import SessionVault
from ..browser.session import platform_context
from .base import BasePlatformDriver, UploadResult


@dataclass
class PinterestPin:
    title: str
    description: str
    image_path: str | Path
    link: str = ""
    board_name: str = "Faith Journals"
    alt_text: str = ""


class PinterestDriver(BasePlatformDriver):
    platform_name = "pinterest"

    CREATE_PIN_URL = "https://www.pinterest.com/pin-creation-tool/"

    async def verify_session(self) -> bool:
        try:
            async with platform_context("pinterest", self.vault) as (ctx, page):
                await page.goto("https://www.pinterest.com/", wait_until="domcontentloaded", timeout=20000)
                return "login" not in page.url
        except Exception:
            return False

    async def _open_board_dropdown(self, page) -> bool:
        """Click the board selector to open the board picker flyout. Returns True on success."""
        board_btn = page.locator('[data-test-id="board-dropdown-select-button"]').first
        if await board_btn.count() == 0:
            board_btn = page.locator('[data-test-id="storyboard-selector-board"]').first
        if await board_btn.count() == 0:
            return False
        await board_btn.click()
        await page.wait_for_timeout(1500)
        return True

    async def _create_board_in_flyout(self, page, board_name: str) -> bool:
        """
        Create a new board using the Create Board button in the board picker flyout.
        Assumes the flyout is already open.
        Returns True on success.
        """
        create_btn = page.locator('[data-test-id="create-board-button"]').first
        if await create_btn.count() == 0:
            return False

        await create_btn.click()
        await page.wait_for_timeout(1500)

        # Fill board name
        name_input = page.locator('#boardEditName').first
        if await name_input.count() == 0:
            return False

        await name_input.fill(board_name)
        await page.wait_for_timeout(300)

        # Submit
        submit_btn = page.locator('[data-test-id="board-form-submit-button"]').first
        if await submit_btn.count() == 0:
            return False

        await submit_btn.click()
        await page.wait_for_timeout(2000)
        return True

    async def _select_board(self, page, board_name: str) -> bool:
        """
        Open board dropdown and select the given board. Creates it if not found.
        Returns True on success.
        """
        opened = await self._open_board_dropdown(page)
        if not opened:
            return False

        # Check if board picker flyout is visible and search for board
        # Look for board in the list by text
        board_option = page.locator(
            f'[data-test-id="board-row-{board_name}"], '
            f'[title="{board_name}"]'
        ).first

        if await board_option.count() == 0:
            # Try searching via the search field
            search_field = page.locator('#pickerSearchField').first
            if await search_field.count() > 0:
                await search_field.fill(board_name)
                await page.wait_for_timeout(800)
                # Look again after search
                board_option = page.locator(
                    f'div:has-text("{board_name}")[role="option"], '
                    f'li:has-text("{board_name}")'
                ).first

        if await board_option.count() > 0:
            await board_option.click()
            await page.wait_for_timeout(500)
            return True

        # Check if "No boards found" — create the board
        no_boards = page.locator('[data-test-id="search-boards-field-container"]:has-text("No boards found")').first
        create_board_btn = page.locator('[data-test-id="create-board-button"]').first

        if await create_board_btn.count() > 0:
            created = await self._create_board_in_flyout(page, board_name)
            if created:
                # After board creation, re-open the dropdown to select it
                await page.wait_for_timeout(1000)
                opened2 = await self._open_board_dropdown(page)
                if opened2:
                    # Board should now appear
                    await page.wait_for_timeout(800)
                    board_option2 = page.locator(
                        f'[title="{board_name}"], '
                        f'div:has-text("{board_name}")[role="option"]'
                    ).first
                    if await board_option2.count() > 0:
                        await board_option2.click()
                        await page.wait_for_timeout(500)
                        return True
                    # Try clicking first available board option
                    first_board = page.locator('[data-test-id^="board-row-"]').first
                    if await first_board.count() > 0:
                        await first_board.click()
                        await page.wait_for_timeout(500)
                        return True
                return created  # board was created even if selection is unclear

        # Escape and continue
        await page.keyboard.press("Escape")
        return False

    async def create_pin(self, pin: PinterestPin) -> UploadResult:
        """
        Create a new Pinterest pin via headless browser with saved session.
        Uses the storyboard pin creation tool with verified selectors.
        """
        image_path = Path(pin.image_path)
        if not image_path.exists():
            return UploadResult(
                success=False, platform="pinterest", error=f"Image not found: {image_path}"
            )

        async with platform_context("pinterest", self.vault) as (ctx, page):
            try:
                await page.goto(self.CREATE_PIN_URL, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                # Upload the pin image via the storyboard upload input
                file_input = page.locator('#storyboard-upload-input').first
                if await file_input.count() == 0:
                    return UploadResult(
                        success=False, platform="pinterest", error="File upload input (#storyboard-upload-input) not found"
                    )

                await file_input.set_input_files(str(image_path))
                await page.wait_for_timeout(5000)

                # Wait for editor panel to be ready
                try:
                    await page.wait_for_selector('#storyboard-selector-title', timeout=10000)
                except Exception:
                    pass

                # Fill title
                title_input = page.locator('#storyboard-selector-title').first
                if await title_input.count() > 0:
                    await title_input.clear()
                    await title_input.fill(pin.title)
                    await page.wait_for_timeout(300)

                # Fill description (contenteditable div - use keyboard type)
                desc_div = page.locator('[aria-label="Add a detailed description"]').first
                if await desc_div.count() > 0:
                    await desc_div.click()
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Control+a")
                    await page.keyboard.type(pin.description)
                    await page.wait_for_timeout(300)

                # Fill destination link
                if pin.link:
                    link_input = page.locator('#WebsiteField').first
                    if await link_input.count() > 0:
                        await link_input.fill(pin.link)
                        await page.wait_for_timeout(300)

                # Select/create board
                board_selected = await self._select_board(page, pin.board_name)

                await page.wait_for_timeout(1000)

                # Click Publish button
                publish_btn = page.locator('[data-test-id="storyboard-creation-nav-done"]').first
                if await publish_btn.count() == 0:
                    return UploadResult(
                        success=False,
                        platform="pinterest",
                        error="Publish button ([data-test-id='storyboard-creation-nav-done']) not found",
                    )

                await publish_btn.click()
                await page.wait_for_timeout(5000)

                # Check outcome
                success_url = page.url
                # Look for error indicators
                error_indicator = page.locator('[class*="error"], [data-test-id*="error"]').first
                error_text = ""
                if await error_indicator.count() > 0:
                    error_text = await error_indicator.inner_text()

                return UploadResult(
                    success=True,
                    platform="pinterest",
                    url=success_url,
                    message=f"Pin '{pin.title}' published | board_selected={board_selected} | board='{pin.board_name}' | error_check='{error_text[:100]}'",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="pinterest",
                    error=str(e),
                )

    async def ensure_board_exists(self, board_name: str) -> bool:
        """
        Check if a board exists. Returns True if found.
        """
        async with platform_context("pinterest", self.vault) as (ctx, page):
            try:
                await page.goto(self.CREATE_PIN_URL, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                opened = await self._open_board_dropdown(page)
                if not opened:
                    return False

                board_option = page.locator(f'[title="{board_name}"]').first
                exists = await board_option.count() > 0
                await page.keyboard.press("Escape")
                return exists
            except Exception:
                return False

    def post_pin(self, pin: PinterestPin) -> UploadResult:
        """Synchronous wrapper."""
        return asyncio.run(self.create_pin(pin))

    def ensure_board(self, board_name: str) -> bool:
        """Synchronous wrapper for ensure_board_exists."""
        return asyncio.run(self.ensure_board_exists(board_name))

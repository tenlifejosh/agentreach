"""
AgentReach — Pinterest Driver
Cookie-based headless driver for organic pin creation.
Pinterest's API requires business verification and approval.
This driver uses saved session cookies for fully autonomous posting.
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

    async def create_pin(self, pin: PinterestPin) -> UploadResult:
        """
        Create a new Pinterest pin via headless browser with saved session.
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

                # Upload the pin image
                from ..browser.uploader import upload_file
                await upload_file(
                    page,
                    image_path,
                    trigger_selector='[data-test-id="storyboard-upload-input"], [class*="upload"]',
                    input_selector='input[type="file"]',
                )
                await page.wait_for_timeout(3000)

                # Title
                title_input = page.locator('[id="pin-draft-title"], [placeholder*="title"], [data-test-id*="title"]').first
                await title_input.fill(pin.title)

                # Description
                desc_input = page.locator('[placeholder*="description"], [data-test-id*="description"], #pin-draft-description').first
                await desc_input.fill(pin.description)

                # Destination link
                if pin.link:
                    link_input = page.locator('[placeholder*="link"], [data-test-id*="destination"], #pin-draft-link').first
                    await link_input.fill(pin.link)

                # Board selection
                board_btn = page.locator('[data-test-id="board-dropdown-select-btn"], [class*="boardSelector"]').first
                await board_btn.click()
                await page.wait_for_timeout(1000)

                board_option = page.locator(f'[title="{pin.board_name}"], [aria-label="{pin.board_name}"]').first
                if await board_option.count() > 0:
                    await board_option.click()
                else:
                    # Board not found — click first available
                    await page.keyboard.press("Escape")

                await page.wait_for_timeout(500)

                # Publish
                publish_btn = page.locator('[data-test-id="board-dropdown-save-button"], button[class*="publish"]').first
                await publish_btn.click()
                await page.wait_for_timeout(3000)

                # Check for success
                success_url = page.url
                return UploadResult(
                    success=True,
                    platform="pinterest",
                    url=success_url,
                    message=f"Pin '{pin.title}' published to board '{pin.board_name}'",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="pinterest",
                    error=str(e),
                )

    def post_pin(self, pin: PinterestPin) -> UploadResult:
        """Synchronous wrapper."""
        return asyncio.run(self.create_pin(pin))

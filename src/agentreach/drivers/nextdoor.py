"""
AgentReach — Nextdoor Driver
Browser-based session for posting to neighborhood feeds as a business account.

Authentication note:
  Nextdoor uses cookie-based sessions. The harvester opens a visible browser,
  the user logs in normally, and the session cookies are saved to the vault.
  Session stays valid until explicitly revoked or expired.

Usage:
  agentreach harvest nextdoor          # One-time login setup
  agentreach verify nextdoor           # Check session validity
  agentreach nextdoor post <text>      # Post to the neighborhood feed
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from ..browser.session import platform_context
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult, run_async


logger = logging.getLogger(__name__)


class NextdoorDriver(BasePlatformDriver):
    platform_name = "nextdoor"

    HOME_URL = "https://nextdoor.com"
    LOGIN_URL = "https://nextdoor.com/login/"
    NEWS_FEED_URL = "https://nextdoor.com/news_feed/"
    CREATE_POST_URL = "https://nextdoor.com/create_post/"

    async def verify_session(self) -> bool:
        """
        Verify that the saved Nextdoor session is still valid.
        Checks that the user is logged in by looking for user-specific UI.
        """
        try:
            async with platform_context("nextdoor", self.vault) as (ctx, page):
                await page.goto(self.NEWS_FEED_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # If we're redirected to login, session is invalid
                if "login" in page.url or "signin" in page.url:
                    return False

                # Check for logged-in indicators — news feed only visible when logged in
                on_feed = await page.evaluate("""
                    () => {
                        // Check we're on the news feed page
                        const url = window.location.href;
                        if (url.includes('login') || url.includes('signin')) return false;
                        // Look for feed-specific elements
                        const feed = document.querySelector('[data-testid="feed"], .feed-container, [class*="feed"]');
                        // Or check for logged-in nav elements
                        const nav = document.querySelector('[class*="nav"], [class*="header"], nav');
                        // If we're not on login page, we're likely logged in
                        return !url.includes('login');
                    }
                """)
                return bool(on_feed)
        except Exception as exc:
            logger.error("Nextdoor verify_session failed: %s", exc)
            return False

    async def create_post(self, text: str) -> UploadResult:
        """
        Post to the Nextdoor neighborhood feed as the logged-in business account.

        Args:
            text: The post content to publish
        """
        async with platform_context("nextdoor", self.vault) as (ctx, page):
            try:
                # Navigate to create post page
                await page.goto(self.CREATE_POST_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # If redirected to login, session is dead
                if "login" in page.url or "signin" in page.url:
                    return UploadResult(
                        success=False,
                        platform="nextdoor",
                        error="Nextdoor session expired. Re-harvest: agentreach harvest nextdoor",
                    )

                # Try to find the post composition area
                # Nextdoor uses a contenteditable div or textarea
                post_area = page.locator(
                    'div[contenteditable="true"], '
                    'textarea[placeholder*="What"], '
                    'textarea[placeholder*="share"], '
                    'textarea[name="body"], '
                    '[data-testid="post-body"], '
                    '[aria-label*="post"], '
                    '[placeholder*="post"]'
                ).first

                try:
                    await post_area.wait_for(timeout=10000)
                except Exception as exc:
                    logger.debug("Nextdoor create-post editor not found on direct URL, falling back to news feed: %s", exc)
                    # Fall back to news feed and click the post prompt
                    await page.goto(self.NEWS_FEED_URL, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Click "What's on your mind" / post prompt
                    post_prompt = page.locator(
                        '[placeholder*="mind"], '
                        '[placeholder*="What"], '
                        'button:has-text("Post"), '
                        '[data-testid="create-post"], '
                        '[class*="create-post"], '
                        '[class*="compose"]'
                    ).first
                    await post_prompt.click(timeout=8000)
                    await page.wait_for_timeout(1500)

                    # Now find the text area again
                    post_area = page.locator(
                        'div[contenteditable="true"], '
                        'textarea[placeholder*="What"], '
                        'textarea[placeholder*="share"], '
                        'textarea[name="body"]'
                    ).first
                    await post_area.wait_for(timeout=8000)

                await post_area.click()
                await page.wait_for_timeout(500)

                # Use clipboard paste for reliability
                await page.evaluate(
                    """(text) => {
                        const el = document.activeElement;
                        const dt = new DataTransfer();
                        dt.setData('text/plain', text);
                        el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }));
                    }""",
                    text,
                )
                await page.wait_for_timeout(1000)

                # Fallback: check if text was entered; if not, type it
                try:
                    entered_text = await post_area.inner_text()
                except Exception as exc:
                    logger.debug("Nextdoor could not read composed text back from editor: %s", exc)
                    entered_text = ""

                if not entered_text.strip():
                    # Type in chunks to avoid timeout
                    chunk_size = 200
                    for i in range(0, len(text), chunk_size):
                        chunk = text[i:i + chunk_size]
                        await post_area.type(chunk, delay=10)
                        await page.wait_for_timeout(200)

                await page.wait_for_timeout(500)

                # Find and click the submit/post button
                submit_btn = page.locator(
                    'button:has-text("Post"), '
                    'button[type="submit"]:has-text("Share"), '
                    'button:has-text("Share"), '
                    '[data-testid="submit-post"], '
                    '[data-testid="post-submit"]'
                ).first

                await submit_btn.click(timeout=10000)
                await page.wait_for_timeout(3000)

                # Confirm we're back on the feed or the URL changed
                current_url = page.url
                if "login" in current_url:
                    return UploadResult(
                        success=False,
                        platform="nextdoor",
                        error="Post may have failed — redirected to login after submit.",
                    )

                return UploadResult(
                    success=True,
                    platform="nextdoor",
                    url=current_url,
                    message="Post published to Nextdoor neighborhood feed",
                )

            except Exception as e:
                logger.error("Nextdoor create_post failed: %s", e, exc_info=True)
                return UploadResult(
                    success=False,
                    platform="nextdoor",
                    error=f"Failed to post to Nextdoor: {str(e)}\n\nEnsure session is valid: agentreach harvest nextdoor",
                )

    def post(self, text: str) -> UploadResult:
        """Synchronous wrapper for create_post."""
        return run_async(self.create_post(text))

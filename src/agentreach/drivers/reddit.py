"""
AgentReach — Reddit Driver
Browser-based session for posting comments, submissions, and community engagement.

Authentication note:
  Reddit uses cookie-based sessions. The harvester opens a visible browser,
  the user logs in normally, and the session cookies are saved to the vault.
  Session stays valid until explicitly revoked or expired (~90 days).

Usage:
  agentreach harvest reddit          # One-time login setup
  agentreach verify reddit           # Check session validity
  agentreach reddit comment <url> <text>   # Post a comment on a thread
  agentreach reddit post <subreddit> <title> <body>  # Create a new post
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from ..browser.session import platform_context
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """Data for creating a new Reddit text post.

    Attributes:
        subreddit: Target subreddit name (without the r/ prefix).
        title:     Post title.
        body:      Post body text.
    """

    subreddit: str
    title: str
    body: str


@dataclass
class RedditComment:
    """Data for posting a comment on a Reddit thread.

    Attributes:
        thread_url: Full URL of the Reddit thread to comment on.
        text:       Comment body text.
    """

    thread_url: str
    text: str


class RedditDriver(BasePlatformDriver):
    platform_name = "reddit"

    HOME_URL = "https://www.reddit.com"
    LOGIN_URL = "https://www.reddit.com/login"

    async def verify_session(self) -> bool:
        """
        Verify that the saved Reddit session is still valid.
        Checks that the user is logged in by looking for user-specific UI.
        """
        try:
            async with platform_context("reddit", self.vault) as (ctx, page):
                await page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if "login" in page.url:
                    return False

                logged_in = await page.evaluate(
                    """
                    () => {
                        const userMenu = document.querySelector('[aria-label*="Profile"], #USER_DROPDOWN_ID, [data-testid="user-menu"]');
                        if (userMenu) return true;
                        const loginBtn = document.querySelector('a[href*="/login"]');
                        return !loginBtn;
                    }
                    """
                )
                return bool(logged_in)
        except Exception as exc:
            logger.error("Reddit verify_session failed: %s", exc)
            return False

    async def post_comment(self, thread_url: str, text: str) -> UploadResult:
        """Navigate to a Reddit thread URL and post a comment."""
        async with platform_context("reddit", self.vault) as (ctx, page):
            try:
                await page.goto(thread_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if "reddit.com" not in page.url:
                    return UploadResult(
                        success=False,
                        platform="reddit",
                        error="Navigation failed — not on Reddit.",
                    )

                comment_box = page.locator(
                    '[data-testid="comment-textarea"], '
                    '[placeholder*="comment"], '
                    'div[contenteditable="true"]'
                ).first

                try:
                    await comment_box.wait_for(timeout=10000)
                    await comment_box.click()
                except Exception as exc:
                    logger.debug("Reddit comment box not immediately available: %s", exc)
                    prompt = page.locator('div[data-click-id="text"], button:has-text("comment")').first
                    await prompt.click(timeout=5000)
                    await page.wait_for_timeout(1000)
                    comment_box = page.locator('div[contenteditable="true"]').first
                    await comment_box.wait_for(timeout=8000)
                    await comment_box.click()

                await page.wait_for_timeout(500)
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

                content_check = await comment_box.inner_text()
                if not content_check.strip():
                    chunk_size = 200
                    for i in range(0, len(text), chunk_size):
                        chunk = text[i:i + chunk_size]
                        await comment_box.type(chunk, delay=5)
                        await page.wait_for_timeout(200)
                await page.wait_for_timeout(500)

                submit_btn = page.locator(
                    'button:has-text("Comment"), '
                    'button[type="submit"]:has-text("Save"), '
                    '[data-testid="comment-submit-button"]'
                ).first
                await submit_btn.click(timeout=8000)
                await page.wait_for_timeout(2000)

                return UploadResult(
                    success=True,
                    platform="reddit",
                    url=thread_url,
                    message=f"Comment posted on {thread_url}",
                )

            except Exception as exc:
                logger.error("Reddit post_comment failed: %s", exc, exc_info=True)
                return UploadResult(
                    success=False,
                    platform="reddit",
                    error=f"Failed to post comment: {exc}\n\nEnsure session is valid: agentreach harvest reddit",
                )

    async def create_post(self, subreddit: str, title: str, body: str) -> UploadResult:
        """Create a new text post in a subreddit."""
        subreddit = subreddit.lstrip("/").lstrip("r/")
        submit_url = f"https://www.reddit.com/r/{subreddit}/submit"

        async with platform_context("reddit", self.vault) as (ctx, page):
            try:
                await page.goto(submit_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if "login" in page.url:
                    return UploadResult(
                        success=False,
                        platform="reddit",
                        error="Reddit session expired. Re-harvest: agentreach harvest reddit",
                    )

                try:
                    text_tab = page.locator(
                        'button:has-text("Text"), '
                        '[data-testid="post-type-text"], '
                        'a[href*="?type=TEXT"]'
                    ).first
                    await text_tab.click(timeout=5000)
                    await page.wait_for_timeout(500)
                except Exception as exc:
                    logger.debug("Reddit text-tab selection skipped/fell back: %s", exc)

                title_input = page.locator(
                    'textarea[placeholder*="Title"], '
                    'input[name="title"], '
                    '[data-testid="post-title-input"]'
                ).first
                await title_input.wait_for(timeout=10000)
                await title_input.click()
                await title_input.fill(title)
                await page.wait_for_timeout(300)

                body_area = page.locator(
                    'div[contenteditable="true"][data-contents], '
                    'div[contenteditable="true"].public-DraftEditor-content, '
                    'div[contenteditable="true"]'
                ).first
                try:
                    await body_area.wait_for(timeout=8000)
                    await body_area.click()
                    await page.wait_for_timeout(300)
                    await body_area.type(body, delay=20)
                except Exception as exc:
                    logger.debug("Reddit rich text body editor unavailable, falling back to textarea: %s", exc)
                    fallback = page.locator('textarea[name="text"], textarea[placeholder*="text"]').first
                    await fallback.fill(body, timeout=5000)

                await page.wait_for_timeout(500)

                submit_btn = page.locator(
                    'button:has-text("Post"), '
                    'button[type="submit"]:not([disabled]), '
                    '[data-testid="submit-button"]'
                ).first
                await submit_btn.click(timeout=8000)
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)

                post_url = page.url
                return UploadResult(
                    success=True,
                    platform="reddit",
                    url=post_url,
                    message=f"Post '{title}' submitted to r/{subreddit}",
                )

            except Exception as exc:
                logger.error("Reddit create_post failed for r/%s: %s", subreddit, exc, exc_info=True)
                return UploadResult(
                    success=False,
                    platform="reddit",
                    error=f"Failed to create post: {exc}\n\nEnsure session is valid: agentreach harvest reddit",
                )

    def comment(self, thread_url: str, text: str) -> UploadResult:
        """Synchronous wrapper for post_comment."""
        return asyncio.run(self.post_comment(thread_url, text))

    def post(self, subreddit: str, title: str, body: str) -> UploadResult:
        """Synchronous wrapper for create_post."""
        return asyncio.run(self.create_post(subreddit, title, body))

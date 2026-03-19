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
from dataclasses import dataclass
from typing import Optional

from ..browser.session import platform_context
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


@dataclass
class RedditPost:
    subreddit: str
    title: str
    body: str


@dataclass
class RedditComment:
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

                # If we're redirected to login, session is invalid
                if "login" in page.url:
                    return False

                # Check for logged-in indicators
                # Reddit shows a user avatar/expand button when logged in
                logged_in = await page.evaluate("""
                    () => {
                        // Check for user menu button (logged-in state)
                        const userMenu = document.querySelector('[aria-label*="Profile"], #USER_DROPDOWN_ID, [data-testid="user-menu"]');
                        if (userMenu) return true;
                        // Check for "Log In" button (logged-out state)
                        const loginBtn = document.querySelector('a[href*="/login"]');
                        return !loginBtn;
                    }
                """)
                return bool(logged_in)
        except Exception:
            return False

    async def post_comment(self, thread_url: str, text: str) -> UploadResult:
        """
        Navigate to a Reddit thread URL and post a comment.

        Args:
            thread_url: Full URL to the Reddit thread (e.g. https://www.reddit.com/r/...)
            text: Comment text to post
        """
        async with platform_context("reddit", self.vault) as (ctx, page):
            try:
                await page.goto(thread_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check we're on a thread page
                if "reddit.com" not in page.url:
                    return UploadResult(
                        success=False,
                        platform="reddit",
                        error="Navigation failed — not on Reddit.",
                    )

                # Click on the comment input box
                # Reddit's comment area uses a contenteditable div
                comment_box = page.locator(
                    '[data-testid="comment-textarea"], '
                    '[placeholder*="comment"], '
                    'div[contenteditable="true"]'
                ).first

                try:
                    await comment_box.wait_for(timeout=10000)
                    await comment_box.click()
                except Exception:
                    # Try clicking the "Add a comment" prompt first
                    prompt = page.locator('div[data-click-id="text"], button:has-text("comment")').first
                    await prompt.click(timeout=5000)
                    await page.wait_for_timeout(1000)
                    comment_box = page.locator('div[contenteditable="true"]').first
                    await comment_box.wait_for(timeout=8000)
                    await comment_box.click()

                await page.wait_for_timeout(500)
                await comment_box.type(text, delay=30)
                await page.wait_for_timeout(500)

                # Submit the comment
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

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="reddit",
                    error=f"Failed to post comment: {str(e)}\n\nEnsure session is valid: agentreach harvest reddit",
                )

    async def create_post(self, subreddit: str, title: str, body: str) -> UploadResult:
        """
        Create a new text post in a subreddit.

        Args:
            subreddit: Subreddit name without r/ prefix (e.g. 'AskReddit')
            title: Post title
            body: Post body text
        """
        # Normalize subreddit name
        subreddit = subreddit.lstrip("/").lstrip("r/")
        submit_url = f"https://www.reddit.com/r/{subreddit}/submit"

        async with platform_context("reddit", self.vault) as (ctx, page):
            try:
                await page.goto(submit_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # If redirected to login, session is dead
                if "login" in page.url:
                    return UploadResult(
                        success=False,
                        platform="reddit",
                        error="Reddit session expired. Re-harvest: agentreach harvest reddit",
                    )

                # Select "Text" post type if tabs are visible
                try:
                    text_tab = page.locator(
                        'button:has-text("Text"), '
                        '[data-testid="post-type-text"], '
                        'a[href*="?type=TEXT"]'
                    ).first
                    await text_tab.click(timeout=5000)
                    await page.wait_for_timeout(500)
                except Exception:
                    pass  # Already on text tab or single-type form

                # Fill title
                title_input = page.locator(
                    'textarea[placeholder*="Title"], '
                    'input[name="title"], '
                    '[data-testid="post-title-input"]'
                ).first
                await title_input.wait_for(timeout=10000)
                await title_input.click()
                await title_input.fill(title)
                await page.wait_for_timeout(300)

                # Fill body
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
                except Exception:
                    # Fallback: look for a textarea
                    fallback = page.locator('textarea[name="text"], textarea[placeholder*="text"]').first
                    await fallback.fill(body, timeout=5000)

                await page.wait_for_timeout(500)

                # Submit the post
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

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="reddit",
                    error=f"Failed to create post: {str(e)}\n\nEnsure session is valid: agentreach harvest reddit",
                )

    def comment(self, thread_url: str, text: str) -> UploadResult:
        """Synchronous wrapper for post_comment."""
        return asyncio.run(self.post_comment(thread_url, text))

    def post(self, subreddit: str, title: str, body: str) -> UploadResult:
        """Synchronous wrapper for create_post."""
        return asyncio.run(self.create_post(subreddit, title, body))

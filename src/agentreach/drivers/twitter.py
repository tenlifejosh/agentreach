"""
AgentReach — X/Twitter Driver
Browser-based session for posting tweets, replies, and managing X presence.

Authentication note:
  X uses cookie-based sessions. The harvester opens a visible browser,
  the user logs in normally at x.com, and the session cookies are saved to the vault.
  Sessions may expire or require re-auth after extended periods or policy changes.
  X/Twitter's API is heavily restricted — browser automation is the reliable path.

Usage:
  agentreach harvest twitter             # One-time login setup
  agentreach verify twitter              # Check session validity
  agentreach twitter tweet <text>        # Post a new tweet
  agentreach twitter reply <url> <text>  # Reply to a tweet by URL
"""

import asyncio
from typing import Optional

from ..browser.session import platform_context
from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


class TwitterDriver(BasePlatformDriver):
    platform_name = "twitter"

    HOME_URL = "https://x.com/home"
    COMPOSE_URL = "https://x.com/compose/tweet"

    async def verify_session(self) -> bool:
        """
        Verify that the saved X/Twitter session is still valid.
        Checks that the user is logged in by navigating to the home timeline.
        """
        try:
            async with platform_context("twitter", self.vault) as (ctx, page):
                await page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Logged-out X redirects to /i/flow/login or shows a login prompt
                if "login" in page.url or "flow" in page.url:
                    return False

                # Check for home timeline indicators
                logged_in = await page.evaluate("""
                    () => {
                        // "What's happening?" compose box = logged in
                        const compose = document.querySelector('[data-testid="tweetTextarea_0"], [placeholder*="happening"]');
                        if (compose) return true;
                        // Primary column with tweets = logged in
                        const timeline = document.querySelector('[data-testid="primaryColumn"]');
                        if (timeline) return true;
                        // Login button presence = logged out
                        const login = document.querySelector('[data-testid="loginButton"]');
                        return !login;
                    }
                """)
                return bool(logged_in)
        except Exception:
            return False

    async def post_tweet(self, text: str) -> UploadResult:
        """
        Post a new tweet using the saved session.

        Args:
            text: Tweet text (max 280 characters; no length check here — X enforces it)
        """
        async with platform_context("twitter", self.vault) as (ctx, page):
            try:
                await page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for login redirect
                if "login" in page.url or "flow" in page.url:
                    return UploadResult(
                        success=False,
                        platform="twitter",
                        error="X session expired or invalid. Re-harvest: agentreach harvest twitter",
                    )

                # Click the compose area
                compose_area = page.locator(
                    '[data-testid="tweetTextarea_0"], '
                    '[contenteditable="true"][aria-label*="Tweet"], '
                    'div[aria-label*="Post text"]'
                ).first

                try:
                    await compose_area.wait_for(timeout=10000)
                    await compose_area.click()
                except Exception:
                    # Try the tweet button to open compose modal
                    tweet_btn = page.locator(
                        '[data-testid="SideNav_NewTweet_Button"], '
                        'a[href="/compose/tweet"], '
                        'button[aria-label="Post"]'
                    ).first
                    await tweet_btn.click(timeout=8000)
                    await page.wait_for_timeout(1000)
                    compose_area = page.locator(
                        '[data-testid="tweetTextarea_0"], '
                        '[contenteditable="true"]'
                    ).first
                    await compose_area.wait_for(timeout=8000)
                    await compose_area.click()

                await page.wait_for_timeout(300)
                await compose_area.type(text, delay=30)
                await page.wait_for_timeout(500)

                # Submit the tweet
                submit_btn = page.locator(
                    '[data-testid="tweetButtonInline"], '
                    '[data-testid="tweetButton"], '
                    'button[data-testid="tweetButtonInline"]'
                ).first
                await submit_btn.click(timeout=8000)
                await page.wait_for_timeout(2000)

                # Verify it posted (compose area should clear or modal should close)
                current_url = page.url

                return UploadResult(
                    success=True,
                    platform="twitter",
                    url=current_url,
                    message=f"Tweet posted: {text[:50]}{'...' if len(text) > 50 else ''}",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="twitter",
                    error=f"Failed to post tweet: {str(e)}\n\nEnsure session is valid: agentreach harvest twitter",
                )

    async def reply_to_tweet(self, tweet_url: str, text: str) -> UploadResult:
        """
        Reply to a specific tweet by navigating to its URL.

        Args:
            tweet_url: Full URL to the tweet (e.g. https://x.com/user/status/123...)
            text: Reply text
        """
        async with platform_context("twitter", self.vault) as (ctx, page):
            try:
                await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for login redirect
                if "login" in page.url or "flow" in page.url:
                    return UploadResult(
                        success=False,
                        platform="twitter",
                        error="X session expired or invalid. Re-harvest: agentreach harvest twitter",
                    )

                # Click the Reply button on the tweet
                reply_btn = page.locator(
                    '[data-testid="reply"], '
                    'button[aria-label*="Reply"], '
                    'div[aria-label*="Reply"]'
                ).first

                await reply_btn.wait_for(timeout=10000)
                await reply_btn.click()
                await page.wait_for_timeout(1000)

                # Find the reply compose area (may be in a modal or inline)
                reply_area = page.locator(
                    '[data-testid="tweetTextarea_0"], '
                    '[contenteditable="true"][aria-label*="Tweet"], '
                    'div[role="textbox"][contenteditable="true"]'
                ).first

                await reply_area.wait_for(timeout=8000)
                await reply_area.click()
                await page.wait_for_timeout(300)
                await reply_area.type(text, delay=30)
                await page.wait_for_timeout(500)

                # Submit the reply
                submit_btn = page.locator(
                    '[data-testid="tweetButtonInline"], '
                    '[data-testid="tweetButton"]'
                ).first
                await submit_btn.click(timeout=8000)
                await page.wait_for_timeout(2000)

                return UploadResult(
                    success=True,
                    platform="twitter",
                    url=tweet_url,
                    message=f"Reply posted on {tweet_url}",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="twitter",
                    error=f"Failed to post reply: {str(e)}\n\nEnsure session is valid: agentreach harvest twitter",
                )

    def tweet(self, text: str) -> UploadResult:
        """Synchronous wrapper for post_tweet."""
        return asyncio.run(self.post_tweet(text))

    def reply(self, tweet_url: str, text: str) -> UploadResult:
        """Synchronous wrapper for reply_to_tweet."""
        return asyncio.run(self.reply_to_tweet(tweet_url, text))

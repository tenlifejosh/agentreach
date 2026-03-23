"""AgentReach — Cookie Harvester.

Opens a VISIBLE browser for the human to log in normally.
Captures and encrypts all session cookies once login is complete.
This is the ONE-TIME setup per platform. After this: fully autonomous.

KDP Note:
    Amazon KDP requires step-up authentication (max_auth_age=0) for all title
    creation and editing operations. After logging in, the harvester instructs
    the user to navigate to the title creation page so those deeper auth cookies
    are captured in the vault. Without this step, the saved session can only
    access the bookshelf (read-only) but not create or edit titles.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright

from ..vault.store import SessionVault

logger = logging.getLogger(__name__)

# Default harvest timeout (seconds)
HARVEST_TIMEOUT: int = 300

# Login URLs per platform
LOGIN_URLS: dict[str, str] = {
    "kdp":      "https://kdp.amazon.com/en_US/signin",
    "etsy":     "https://www.etsy.com/signin",
    "gumroad":  "https://gumroad.com/login",
    "pinterest": "https://www.pinterest.com/login/",
    "reddit":   "https://www.reddit.com/login",
    "twitter":  "https://x.com/i/flow/login",
    "tiktok":   "https://www.tiktok.com/login",
    "nextdoor": "https://nextdoor.com/login/",
}

# URL patterns that confirm a successful login
POST_LOGIN_URL_PATTERNS: dict[str, str] = {
    "kdp":      "kdp.amazon.com/en_US/bookshelf",
    "etsy":     "etsy.com/your/shops",
    "gumroad":  "gumroad.com/dashboard",
    "pinterest": "pinterest.com/home_feed",
    "reddit":   "reddit.com/r/",
    "twitter":  "x.com/home",
    "tiktok":   "tiktok.com/foryou",
    "nextdoor": "nextdoor.com/news_feed",
}

# Post-login deep-navigation steps for platforms that require step-up auth cookies.
# Each entry provides a URL pattern to wait for plus user instructions.
POST_LOGIN_DEEP_STEPS: dict[str, dict[str, str]] = {
    "kdp": {
        "pattern": "kdp.amazon.com/en_US/title-setup",
        "instructions": (
            "✅ Logged in! For KDP to work autonomously, complete one more step:\n"
            "   → Click '+ Create a new title' (or 'Paperback') to open the book creation form.\n"
            "   → Wait for the title/details form to fully load.\n"
            "   → AgentReach will capture the full auth state and then close automatically."
        ),
    },
}


async def harvest_session(
    platform: str,
    vault: Optional[SessionVault] = None,
    timeout: int = HARVEST_TIMEOUT,
) -> dict:
    """Open a visible browser, let the human log in, then save the encrypted session.

    For platforms with step-up authentication (e.g. KDP), also waits for the
    user to navigate to a deeper page so that the required elevated-auth cookies
    are captured alongside the standard session cookies.

    Args:
        platform: Platform identifier (e.g. 'kdp', 'etsy'). Must be a key in
                  ``LOGIN_URLS``.
        vault:    SessionVault to save the harvested session into. A new default
                  vault is created if omitted.
        timeout:  Seconds to wait for the human to complete the login flow
                  (default: 300 seconds / 5 minutes).

    Returns:
        The harvested session data dict (also saved to vault).

    Raises:
        ValueError: If the platform is not recognised.
    """
    if vault is None:
        vault = SessionVault()

    platform = platform.lower()
    login_url = LOGIN_URLS.get(platform)
    if not login_url:
        raise ValueError(
            f"Unknown platform: '{platform}'. "
            f"Supported platforms: {sorted(LOGIN_URLS.keys())}"
        )

    post_login_pattern = POST_LOGIN_URL_PATTERNS.get(platform, "")
    deep_step = POST_LOGIN_DEEP_STEPS.get(platform)

    logger.info(
        "AgentReach: starting session harvest for %s (timeout=%ds)",
        platform.upper(),
        timeout,
    )
    print(f"\n🌐 AgentReach — Harvesting session for: {platform.upper()}")
    print(f"   A browser window will open. Log in normally.")
    print(f"   AgentReach will detect when you're done automatically.")
    print(f"   You have {timeout // 60} minutes.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        await page.goto(login_url)
        print(f"   Browser opened → {login_url}")
        print("   Waiting for login to complete...")

        # Wait for post-login URL or let the timeout expire
        try:
            if post_login_pattern:
                await page.wait_for_url(
                    f"**{post_login_pattern}**",
                    timeout=timeout * 1000,
                    wait_until="domcontentloaded",
                )
            else:
                await asyncio.sleep(timeout)
        except Exception:
            print("   ⚠️  Timed out waiting for login — capturing session anyway...")

        # Phase 2: platforms requiring deep auth (e.g. KDP title-creation cookies)
        if deep_step:
            deep_pattern = deep_step["pattern"]
            deep_instructions = deep_step["instructions"]

            print(f"\n   {deep_instructions}\n")

            try:
                await page.wait_for_url(
                    f"**{deep_pattern}**",
                    timeout=timeout * 1000,
                    wait_until="domcontentloaded",
                )
                logger.info("AgentReach: deep-auth page reached: %s", page.url)
                # Allow all auth cookies to settle before harvesting
                await page.wait_for_timeout(3000)
            except Exception:
                print(
                    "   ⚠️  Timed out waiting for deep-auth step. "
                    "Capturing session anyway (may have limited access)..."
                )

        # Harvest all cookies and storage state
        cookies = await context.cookies()
        storage_state = await context.storage_state()

        # Merge with any existing vault data (preserves API tokens set separately)
        existing = vault.load(platform) or {}
        session_data = {
            **existing,
            "platform": platform,
            "harvested_at": datetime.now(timezone.utc).isoformat(),
            "cookies": cookies,
            "storage_state": storage_state,
            "login_url": login_url,
        }

        vault.save(platform, session_data)
        await browser.close()

    logger.info("AgentReach: session harvested and encrypted for %s", platform.upper())
    print(f"\n   ✅ Session harvested and encrypted for {platform.upper()}")
    print(f"   Stored at: ~/.agentreach/vault/{platform}.vault")
    print(f"   AgentReach is now fully autonomous for {platform.upper()}.\n")

    return session_data


def harvest(
    platform: str,
    vault: Optional[SessionVault] = None,
    timeout: int = HARVEST_TIMEOUT,
) -> dict:
    """Synchronous wrapper for :func:`harvest_session`.

    Args:
        platform: Platform identifier (e.g. 'kdp', 'etsy').
        vault:    SessionVault to save the session into.
        timeout:  Seconds to wait for login completion.

    Returns:
        The harvested session data dict.
    """
    return asyncio.run(harvest_session(platform, vault, timeout))

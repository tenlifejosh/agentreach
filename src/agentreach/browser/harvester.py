"""
AgentReach — Cookie Harvester
Opens a VISIBLE browser for the human to log in normally.
Captures and encrypts all session cookies once login is complete.
This is the ONE TIME setup per platform. After this: fully autonomous.

KDP Note (2026-03-14):
  Amazon KDP requires 'step-up authentication' (max_auth_age=0) for all title
  creation and editing operations. After logging in, the harvester instructs the
  user to navigate to the title creation page so those deeper auth cookies are
  captured in the vault. Without this step, the saved session can only access
  the bookshelf (read-only) but not create or edit titles.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

from ..vault.store import SessionVault


# Login URLs per platform
LOGIN_URLS = {
    "kdp": "https://kdp.amazon.com/en_US/signin",
    "etsy": "https://www.etsy.com/signin",
    "gumroad": "https://gumroad.com/login",
    "pinterest": "https://www.pinterest.com/login/",
    "reddit": "https://www.reddit.com/login",
    "twitter": "https://x.com/i/flow/login",
    "tiktok": "https://www.tiktok.com/login",
}

# Signals that login is complete (URL patterns to wait for)
POST_LOGIN_URL_PATTERNS = {
    "kdp": "kdp.amazon.com/en_US/bookshelf",
    "etsy": "etsy.com/your/shops",
    "gumroad": "gumroad.com/dashboard",
    "pinterest": "pinterest.com/home_feed",
    "reddit": "reddit.com/r/",
    "twitter": "x.com/home",
    "tiktok": "tiktok.com/foryou",
}

# For some platforms, after the initial login we need the user to navigate
# to a deeper page to capture step-up auth cookies.
# The key is the URL pattern to wait for; value is instructions shown to the user.
POST_LOGIN_DEEP_STEPS = {
    "kdp": {
        "pattern": "kdp.amazon.com/en_US/title-setup",
        "instructions": (
            "✅ Logged in! Now for KDP to work autonomously, do ONE more thing:\n"
            "   → Click '+ Create a new title' (or 'Paperback') to open the book creation form.\n"
            "   → Wait for the title/details form to fully load.\n"
            "   → AgentReach will capture the full auth state and then close automatically."
        ),
    },
}

# How long to wait for the human to complete login (seconds)
HARVEST_TIMEOUT = 300  # 5 minutes


async def harvest_session(
    platform: str,
    vault: Optional[SessionVault] = None,
    timeout: int = HARVEST_TIMEOUT,
) -> dict:
    """
    Open a visible browser, let the human log in, then save the session.

    For KDP: Also waits for the user to navigate to the title creation form
    to capture step-up authentication cookies needed for autonomous operation.

    Returns the harvested session data.
    """
    if vault is None:
        vault = SessionVault()

    platform = platform.lower()
    login_url = LOGIN_URLS.get(platform)
    if not login_url:
        raise ValueError(f"Unknown platform: {platform}. Known: {list(LOGIN_URLS.keys())}")

    post_login_pattern = POST_LOGIN_URL_PATTERNS.get(platform, "")
    deep_step = POST_LOGIN_DEEP_STEPS.get(platform)

    print(f"\n🌐 AgentReach — Harvesting session for: {platform.upper()}")
    print(f"   A browser window will open. Log in normally.")
    print(f"   AgentReach will detect when you're done automatically.")
    print(f"   You have {timeout // 60} minutes.\n")

    async with async_playwright() as p:
        # Launch VISIBLE browser (not headless) so human can interact
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--start-maximized"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        await page.goto(login_url)
        print(f"   Browser opened → {login_url}")
        print(f"   Waiting for login to complete...")

        # Wait for post-login URL or timeout
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
            print(f"   ⚠️  Timed out waiting for login. Capturing session anyway...")

        # Phase 2: For platforms needing deep auth, wait for the user to navigate further
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
                print(f"   ✅ Deep auth page reached: {page.url}")
                # Wait a moment for all auth cookies to be fully set
                await page.wait_for_timeout(3000)
            except Exception:
                print(f"   ⚠️  Timed out waiting for deep auth step. "
                      f"Capturing session anyway (may have limited access)...")

        # Harvest everything
        cookies = await context.cookies()
        storage_state = await context.storage_state()

        # Merge with existing vault data (preserve things like API tokens)
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

    print(f"\n   ✅ Session harvested and encrypted for {platform.upper()}")
    print(f"   Stored at: ~/.agentreach/vault/{platform}.vault")
    print(f"   AgentReach is now fully autonomous for {platform.upper()}.\n")

    return session_data


def harvest(platform: str, vault: Optional[SessionVault] = None, timeout: int = HARVEST_TIMEOUT):
    """Synchronous wrapper for harvest_session."""
    return asyncio.run(harvest_session(platform, vault, timeout))
# TikTok added

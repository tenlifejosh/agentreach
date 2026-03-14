"""
AgentReach — Cookie Harvester
Opens a VISIBLE browser for the human to log in normally.
Captures and encrypts all session cookies once login is complete.
This is the ONE TIME setup per platform. After this: fully autonomous.
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
}

# Signals that login is complete (URL patterns to wait for)
POST_LOGIN_URL_PATTERNS = {
    "kdp": "kdp.amazon.com/en_US/bookshelf",
    "etsy": "etsy.com/your/shops",
    "gumroad": "gumroad.com/dashboard",
    "pinterest": "pinterest.com/",
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

    Returns the harvested session data.
    """
    if vault is None:
        vault = SessionVault()

    platform = platform.lower()
    login_url = LOGIN_URLS.get(platform)
    if not login_url:
        raise ValueError(f"Unknown platform: {platform}. Known: {list(LOGIN_URLS.keys())}")

    post_login_pattern = POST_LOGIN_URL_PATTERNS.get(platform, "")

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

        # Harvest everything
        cookies = await context.cookies()
        storage_state = await context.storage_state()

        session_data = {
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

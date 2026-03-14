"""
AgentReach — Headless Session Manager
Loads saved encrypted sessions into a headless Playwright context.
The core engine that makes autonomous operation possible.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from ..vault.store import SessionVault
from ..vault.health import check_session, SessionStatus


class SessionNotFoundError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


@asynccontextmanager
async def platform_context(
    platform: str,
    vault: Optional[SessionVault] = None,
    headless: bool = True,
    check_health: bool = True,
) -> AsyncGenerator[tuple[BrowserContext, Page], None]:
    """
    Context manager: yields an authenticated (BrowserContext, Page) for a platform.

    Usage:
        async with platform_context("kdp") as (ctx, page):
            await page.goto("https://kdp.amazon.com/en_US/bookshelf")
            # page is already authenticated
    """
    if vault is None:
        vault = SessionVault()

    platform = platform.lower()

    # Health check
    if check_health:
        health = check_session(platform, vault)
        if health.status == SessionStatus.MISSING:
            raise SessionNotFoundError(
                f"No session for '{platform}'. Run: agentreach harvest {platform}"
            )
        if health.status == SessionStatus.EXPIRED:
            raise SessionExpiredError(
                f"Session for '{platform}' has expired. Run: agentreach harvest {platform}"
            )

    # Load session data
    session_data = vault.load(platform)
    if not session_data:
        raise SessionNotFoundError(f"Failed to load session for '{platform}'")

    storage_state = session_data.get("storage_state", {})
    cookies = session_data.get("cookies", [])

    # If storage_state has cookies embedded, use that directly
    # Otherwise build it from the cookies list
    if not storage_state.get("cookies") and cookies:
        storage_state = {"cookies": cookies, "origins": []}

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        context: BrowserContext = await browser.new_context(
            storage_state=storage_state if storage_state else None,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Add cookies directly if storage_state didn't capture them
        if cookies and not storage_state.get("cookies"):
            await context.add_cookies(cookies)

        page: Page = await context.new_page()

        try:
            yield context, page
        finally:
            await browser.close()

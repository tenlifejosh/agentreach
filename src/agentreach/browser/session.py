"""
AgentReach — Headless Session Manager
Loads saved encrypted sessions into a headless Playwright context.
The core engine that makes autonomous operation possible.
"""

from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..vault.health import SessionStatus, check_session
from ..vault.store import SessionVault, VaultCorruptedError

try:
    from playwright_stealth import stealth_async
except ImportError:  # pragma: no cover - optional dependency fallback only
    stealth_async = None


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
        if health.status == SessionStatus.UNKNOWN:
            raise SessionNotFoundError(health.message)

    try:
        session_data = vault.load(platform)
    except VaultCorruptedError as exc:
        raise SessionNotFoundError(str(exc)) from exc

    if not session_data:
        raise SessionNotFoundError(f"Failed to load session for '{platform}'")

    storage_state = session_data.get("storage_state", {})
    cookies = session_data.get("cookies", [])

    if not storage_state.get("cookies") and cookies:
        storage_state = {"cookies": cookies, "origins": []}

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
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

        if cookies and not storage_state.get("cookies"):
            await context.add_cookies(cookies)

        page: Page = await context.new_page()

        if stealth_async is not None:
            await stealth_async(page)

        try:
            yield context, page
        finally:
            await browser.close()

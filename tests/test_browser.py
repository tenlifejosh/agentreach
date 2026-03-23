"""
Tests for AgentReach Browser Layer — session loading, context manager, error handling
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

from agentreach.browser.session import (
    platform_context,
    SessionNotFoundError,
    SessionExpiredError,
)
from tests.conftest import save_with_timestamp


# ── Session Loading Error Cases ────────────────────────────────────────────────

class TestPlatformContextErrors:
    @pytest.mark.asyncio
    async def test_raises_session_not_found_for_missing(self, vault):
        with pytest.raises(SessionNotFoundError) as exc_info:
            async with platform_context("kdp", vault):
                pass
        assert "kdp" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_session_expired_for_expired(self, vault):
        old_time = datetime.now(timezone.utc) - timedelta(days=90)
        save_with_timestamp(vault, "kdp", old_time)
        with pytest.raises(SessionExpiredError) as exc_info:
            async with platform_context("kdp", vault):
                pass
        assert "kdp" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_not_found_if_vault_load_fails(self, vault):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        save_with_timestamp(vault, "kdp", recent)

        original_load = vault.load
        call_count = [0]

        def patched_load(platform):
            call_count[0] += 1
            if call_count[0] > 1:
                return None
            return original_load(platform)

        vault.load = patched_load

        with pytest.raises(SessionNotFoundError):
            async with platform_context("kdp", vault, check_health=True):
                pass

    @pytest.mark.asyncio
    async def test_no_health_check_skips_check(self, vault):
        with pytest.raises(SessionNotFoundError):
            async with platform_context("kdp", vault, check_health=False):
                pass


# ── Session Loading Success Cases ─────────────────────────────────────────────

class TestPlatformContextSuccess:
    @pytest.mark.asyncio
    async def test_context_loads_cookies_from_storage_state(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc), {
            "cookies": [],
            "storage_state": {
                "cookies": [{"name": "session", "value": "abc", "domain": ".amazon.com"}],
                "origins": [],
            },
        })

        mock_page = AsyncMock()
        mock_page.url = "https://kdp.amazon.com/bookshelf"

        mock_ctx = AsyncMock()
        mock_ctx.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        class MockPlaywright:
            chromium = mock_chromium

        @asynccontextmanager
        async def mock_async_playwright():
            yield MockPlaywright()

        from unittest.mock import patch
        with patch("agentreach.browser.session.async_playwright", mock_async_playwright):
            async with platform_context("kdp", vault) as (ctx, page):
                assert ctx is mock_ctx
                assert page is mock_page

            kwargs = mock_browser.new_context.call_args.kwargs
            assert kwargs["storage_state"]["cookies"][0]["name"] == "session"

    @pytest.mark.asyncio
    async def test_context_builds_storage_state_from_cookies(self, vault):
        cookies = [{"name": "session", "value": "token", "domain": ".amazon.com"}]
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc), {
            "cookies": cookies,
            "storage_state": {"cookies": [], "origins": []},
        })

        mock_page = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        class MockPlaywright:
            chromium = mock_chromium

        @asynccontextmanager
        async def mock_async_playwright():
            yield MockPlaywright()

        from unittest.mock import patch
        with patch("agentreach.browser.session.async_playwright", mock_async_playwright):
            async with platform_context("kdp", vault):
                pass

            kwargs = mock_browser.new_context.call_args.kwargs
            assert kwargs["storage_state"]["cookies"] == cookies
            mock_ctx.add_cookies.assert_not_called()

    @pytest.mark.asyncio
    async def test_browser_closes_on_exit(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc), {
            "storage_state": {"cookies": [{"name": "s", "value": "t", "domain": ".amazon.com"}], "origins": []},
        })

        mock_page = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        class MockPlaywright:
            chromium = mock_chromium

        @asynccontextmanager
        async def mock_async_playwright():
            yield MockPlaywright()

        from unittest.mock import patch
        with patch("agentreach.browser.session.async_playwright", mock_async_playwright):
            async with platform_context("kdp", vault):
                pass

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_closes_on_exception(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc), {
            "storage_state": {"cookies": [{"name": "s", "value": "t", "domain": ".amazon.com"}], "origins": []},
        })

        mock_page = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        class MockPlaywright:
            chromium = mock_chromium

        @asynccontextmanager
        async def mock_async_playwright():
            yield MockPlaywright()

        from unittest.mock import patch
        with patch("agentreach.browser.session.async_playwright", mock_async_playwright):
            with pytest.raises(ValueError):
                async with platform_context("kdp", vault):
                    raise ValueError("Test error")

        mock_browser.close.assert_called_once()


class TestSessionErrors:
    def test_session_not_found_error_is_exception(self):
        err = SessionNotFoundError("no session for kdp")
        assert isinstance(err, Exception)
        assert "kdp" in str(err)

    def test_session_expired_error_is_exception(self):
        err = SessionExpiredError("session expired for etsy")
        assert isinstance(err, Exception)
        assert "etsy" in str(err)

    def test_errors_are_distinct_types(self):
        assert SessionNotFoundError is not SessionExpiredError

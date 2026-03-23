"""
Tests for AgentReach Harvester — login flow, session capture, error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from agentreach.browser.harvester import (
    harvest_session,
    harvest,
    LOGIN_URLS,
    POST_LOGIN_URL_PATTERNS,
    POST_LOGIN_DEEP_STEPS,
    HARVEST_TIMEOUT,
)
from agentreach.vault.store import SessionVault


# ── Constants ──────────────────────────────────────────────────────────────────

class TestHarvesterConstants:
    def test_all_known_platforms_have_login_urls(self):
        platforms = ["kdp", "etsy", "gumroad", "pinterest", "reddit", "twitter", "tiktok", "nextdoor"]
        for p in platforms:
            assert p in LOGIN_URLS, f"Missing login URL for {p}"

    def test_login_urls_are_https(self):
        for platform, url in LOGIN_URLS.items():
            assert url.startswith("https://"), f"{platform} URL not HTTPS: {url}"

    def test_kdp_has_deep_step(self):
        """KDP requires deep step auth capture."""
        assert "kdp" in POST_LOGIN_DEEP_STEPS
        assert "pattern" in POST_LOGIN_DEEP_STEPS["kdp"]
        assert "instructions" in POST_LOGIN_DEEP_STEPS["kdp"]

    def test_default_timeout(self):
        assert HARVEST_TIMEOUT == 300


# ── harvest_session ────────────────────────────────────────────────────────────

class TestHarvestSession:
    def _make_mock_playwright(self, page_url="https://kdp.amazon.com/en_US/bookshelf"):
        """Helper to build mock playwright stack."""
        mock_page = AsyncMock()
        mock_page.url = page_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_url = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.cookies = AsyncMock(return_value=[
            {"name": "session", "value": "harvested_token", "domain": ".amazon.com"}
        ])
        mock_ctx.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})
        mock_ctx.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)
        mock_browser.close = AsyncMock()

        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = AsyncMock()
        mock_pw.chromium = mock_chromium

        return mock_pw, mock_browser, mock_ctx, mock_page

    @pytest.mark.asyncio
    async def test_unknown_platform_raises(self, vault):
        """harvest_session raises ValueError for unknown platform."""
        with pytest.raises(ValueError) as exc_info:
            await harvest_session("unknown_xyz_platform", vault)
        assert "unknown" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_saves_session_to_vault(self, vault, capsys):
        """harvest_session saves cookies to vault after login."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("gumroad", vault, timeout=1)

        # Should have saved to vault
        session = vault.load("gumroad")
        assert session is not None
        assert "cookies" in session

    @pytest.mark.asyncio
    async def test_returns_session_data(self, vault, capsys):
        """harvest_session returns the session dict."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("reddit", vault, timeout=1)

        assert isinstance(result, dict)
        assert "cookies" in result
        assert "platform" in result
        assert result["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_session_has_harvested_at(self, vault, capsys):
        """Harvested session includes harvested_at timestamp."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("etsy", vault, timeout=1)

        assert "harvested_at" in result

    @pytest.mark.asyncio
    async def test_merges_existing_vault_data(self, vault, capsys):
        """harvest_session preserves existing vault data (e.g., API tokens)."""
        vault.save("gumroad", {"access_token": "existing_api_token", "platform": "gumroad"})

        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("gumroad", vault, timeout=1)

        # Existing data should be preserved
        session = vault.load("gumroad")
        assert session.get("access_token") == "existing_api_token"

    @pytest.mark.asyncio
    async def test_platform_normalized_to_lowercase(self, vault, capsys):
        """Platform name is normalized to lowercase."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("KDP", vault, timeout=1)

        assert result["platform"] == "kdp"

    @pytest.mark.asyncio
    async def test_browser_is_closed_after_harvest(self, vault, capsys):
        """Browser is closed after harvesting."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            await harvest_session("reddit", vault, timeout=1)

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_on_login_captures_anyway(self, vault, capsys):
        """harvest_session captures session even when login times out."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()
        # Make wait_for_url throw a timeout
        mock_page.wait_for_url = AsyncMock(side_effect=Exception("Timeout"))

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("kdp", vault, timeout=1)

        # Should still capture and return data
        assert result is not None

    @pytest.mark.asyncio
    async def test_kdp_has_deep_auth_step(self, vault, capsys):
        """KDP harvest shows deep step instructions."""
        mock_pw, mock_browser, mock_ctx, mock_page = self._make_mock_playwright()
        mock_page.wait_for_url = AsyncMock(side_effect=[None, None])  # Both steps succeed

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_pw

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = await harvest_session("kdp", vault, timeout=1)

        # KDP harvest should complete without error
        assert result is not None


# ── harvest (sync wrapper) ─────────────────────────────────────────────────────

class TestHarvestSync:
    def test_harvest_runs_asyncio(self, vault, capsys):
        """Sync harvest() wrapper runs the async function."""
        mock_pw = MagicMock()
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.cookies = AsyncMock(return_value=[])
        mock_ctx.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})
        mock_page = AsyncMock()
        mock_ctx.new_page = AsyncMock(return_value=mock_page)
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium = mock_chromium

        @asynccontextmanager
        async def mock_async_playwright():
            yield mock_playwright_instance

        with patch("agentreach.browser.harvester.async_playwright", mock_async_playwright):
            result = harvest("pinterest", vault=vault, timeout=1)

        assert result is not None
        assert isinstance(result, dict)

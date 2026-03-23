"""
Tests for AgentReach Edge Cases — missing files, corrupt vault, expired sessions, network failures
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from agentreach.vault.store import _FERNET, VaultCorruptedError
from agentreach.vault.health import check_session, SessionStatus
from tests.conftest import save_with_timestamp


# ── Missing Files ──────────────────────────────────────────────────────────────

class TestMissingFiles:
    def test_vault_load_nonexistent_platform(self, vault):
        assert vault.load("this_platform_does_not_exist") is None

    def test_vault_exists_for_missing(self, vault):
        assert vault.exists("missing_platform") is False

    def test_vault_delete_missing_no_error(self, vault):
        vault.delete("this_does_not_exist")

    def test_check_session_missing_vault_file(self, vault):
        result = check_session("nonexistent", vault)
        assert result.status == SessionStatus.MISSING

    @pytest.mark.asyncio
    async def test_kdp_upload_missing_manuscript(self, vault, tmp_path, sample_cover_pdf):
        from agentreach.drivers.kdp import KDPDriver, KDPBookDetails
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        driver = KDPDriver(vault=vault)
        result = await driver.create_paperback(
            KDPBookDetails(title="Test"),
            manuscript_path=tmp_path / "missing.pdf",
            cover_path=sample_cover_pdf,
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_kdp_upload_missing_cover(self, vault, tmp_path, sample_pdf):
        from agentreach.drivers.kdp import KDPDriver, KDPBookDetails
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        driver = KDPDriver(vault=vault)
        result = await driver.create_paperback(
            KDPBookDetails(title="Test"),
            manuscript_path=sample_pdf,
            cover_path=tmp_path / "missing_cover.pdf",
        )
        assert result.success is False
        assert "not found" in result.error.lower()


# ── Corrupt Vault ──────────────────────────────────────────────────────────────

class TestCorruptVault:
    def test_corrupt_vault_file_raises(self, vault):
        path = vault._path("kdp")
        path.write_bytes(b"this_is_not_encrypted_data_at_all!@#$%")
        with pytest.raises(VaultCorruptedError):
            vault.load("kdp")

    def test_partially_corrupt_file_raises(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        original = path.read_bytes()
        path.write_bytes(original[: len(original) // 2])
        with pytest.raises(VaultCorruptedError):
            vault.load("kdp")

    def test_wrong_key_data_raises(self, vault):
        from cryptography.fernet import Fernet

        other_fernet = Fernet(Fernet.generate_key())
        path = vault._path("kdp")
        path.write_bytes(other_fernet.encrypt(json.dumps({"k": "v"}).encode()))

        with pytest.raises(VaultCorruptedError):
            vault.load("kdp")

    def test_json_corruption_inside_encrypted_raises(self, vault):
        path = vault._path("kdp")
        path.write_bytes(_FERNET.encrypt(b"this is not json!"))
        with pytest.raises(VaultCorruptedError):
            vault.load("kdp")

    def test_empty_vault_file_raises(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        path.write_bytes(b"")
        with pytest.raises(VaultCorruptedError):
            vault.load("kdp")

    def test_health_check_with_corrupt_vault_returns_unknown(self, vault):
        path = vault._path("kdp")
        path.write_bytes(b"corrupt_data")
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.UNKNOWN


# ── Expired Sessions ───────────────────────────────────────────────────────────

class TestExpiredSessions:
    def test_expired_session_health_check(self, vault):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        save_with_timestamp(vault, "kdp", old)
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.EXPIRED

    def test_expired_session_negative_days_remaining(self, vault):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        save_with_timestamp(vault, "kdp", old)
        result = check_session("kdp", vault)
        assert result.days_remaining < 0

    def test_expired_session_message_includes_harvest_command(self, vault):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        save_with_timestamp(vault, "kdp", old)
        result = check_session("kdp", vault)
        assert "harvest" in result.message.lower()

    def test_require_valid_session_exits_on_expired(self, vault):
        from agentreach.drivers.base import BasePlatformDriver

        class MockDriver(BasePlatformDriver):
            platform_name = "kdp"
            async def verify_session(self):
                return False

        old = datetime.now(timezone.utc) - timedelta(days=100)
        save_with_timestamp(vault, "kdp", old)
        driver = MockDriver(vault=vault)

        with pytest.raises(SystemExit) as exc:
            driver.require_valid_session()
        assert exc.value.code == 1

    def test_expired_session_in_browser_context(self, vault):
        import asyncio
        from agentreach.browser.session import platform_context, SessionExpiredError

        old = datetime.now(timezone.utc) - timedelta(days=100)
        save_with_timestamp(vault, "kdp", old)

        async def run():
            async with platform_context("kdp", vault):
                pass

        with pytest.raises(SessionExpiredError):
            asyncio.run(run())


# ── Network Failures ───────────────────────────────────────────────────────────

class TestNetworkFailures:
    @pytest.mark.asyncio
    async def test_gumroad_verify_session_network_error(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver

        driver = GumroadDriver(access_token="some_token", vault=vault)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await driver.verify_session()
            assert result is False

    @pytest.mark.asyncio
    async def test_etsy_create_listing_api_error(self, vault):
        from agentreach.drivers.etsy import EtsyDriver, EtsyListing

        vault.save("etsy", {"api_key": "key", "access_token": "token", "shop_id": "shop123"})
        driver = EtsyDriver(vault=vault)
        listing = EtsyListing(title="Test", description="Desc", price=7.99)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await driver.create_listing(listing)
            assert result.success is False
            assert "500" in result.error or "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_gumroad_get_sales_api_error(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver

        vault.save("gumroad", {"access_token": "token"})
        driver = GumroadDriver(access_token="token", vault=vault)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock(side_effect=Exception("429 Rate Limited"))
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            with pytest.raises(Exception):
                await driver.get_sales()

    @pytest.mark.asyncio
    async def test_kdp_upload_step_up_auth_redirect(self, vault, sample_pdf, sample_cover_pdf):
        from agentreach.drivers.kdp import KDPDriver, KDPBookDetails
        from contextlib import asynccontextmanager

        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc), {
            "storage_state": {"cookies": [{"name": "s", "value": "t", "domain": ".amazon.com"}], "origins": []}
        })
        driver = KDPDriver(vault=vault)
        details = KDPBookDetails(title="Test Book")

        mock_page = AsyncMock()
        mock_page.url = "https://www.amazon.com/signin?openid.return_to=..."
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.kdp.platform_context", mock_platform_context):
            result = await driver.create_paperback(details, sample_pdf, sample_cover_pdf)

        assert result.success is False
        assert "step-up" in result.error.lower() or "auth" in result.error.lower() or "signin" in result.error.lower()


# ── Driver Error Handling ──────────────────────────────────────────────────────

class TestDriverErrorHandling:
    @pytest.mark.asyncio
    async def test_driver_handles_playwright_exception(self, vault):
        from agentreach.drivers.reddit import RedditDriver
        from contextlib import asynccontextmanager

        save_with_timestamp(vault, "reddit", datetime.now(timezone.utc))
        driver = RedditDriver(vault=vault)

        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            mock_page = AsyncMock()
            mock_page.url = "https://www.reddit.com/r/test/"
            mock_page.goto = AsyncMock(side_effect=Exception("Browser crashed"))
            mock_page.wait_for_timeout = AsyncMock()
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.reddit.platform_context", mock_platform_context):
            result = await driver.post_comment("https://www.reddit.com/r/test/", "hello")

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_nextdoor_driver_handles_exception(self, vault):
        from agentreach.drivers.nextdoor import NextdoorDriver
        from contextlib import asynccontextmanager

        save_with_timestamp(vault, "nextdoor", datetime.now(timezone.utc))
        driver = NextdoorDriver(vault=vault)

        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            mock_page = AsyncMock()
            mock_page.url = "https://nextdoor.com/create_post/"
            mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
            mock_page.wait_for_timeout = AsyncMock()
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.nextdoor.platform_context", mock_platform_context):
            result = await driver.create_post("Hello!")

        assert result.success is False
        assert result.error is not None

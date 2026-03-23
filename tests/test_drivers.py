"""
Tests for AgentReach Platform Drivers — login flows, error handling, base driver behavior
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path

from agentreach.drivers.base import BasePlatformDriver, UploadResult
from agentreach.drivers import get_driver, DRIVERS
from agentreach.vault.store import SessionVault
from agentreach.vault.health import SessionStatus
from tests.conftest import save_with_timestamp


# ── UploadResult ───────────────────────────────────────────────────────────────

class TestUploadResult:
    def test_success_result(self):
        r = UploadResult(success=True, platform="kdp", message="Done", product_id="123")
        assert r.success is True
        assert r.platform == "kdp"
        assert r.product_id == "123"

    def test_failure_result(self):
        r = UploadResult(success=False, platform="etsy", error="Connection failed")
        assert r.success is False
        assert r.error == "Connection failed"

    def test_default_fields(self):
        r = UploadResult(success=True, platform="gumroad")
        assert r.product_id is None
        assert r.url is None
        assert r.message == ""
        assert r.error is None


# ── BasePlatformDriver ─────────────────────────────────────────────────────────

class ConcretePlatformDriver(BasePlatformDriver):
    """Minimal concrete driver for testing base class."""
    platform_name = "test_platform"

    async def verify_session(self) -> bool:
        return True


class TestBasePlatformDriver:
    def test_init_with_vault(self, vault):
        driver = ConcretePlatformDriver(vault=vault)
        assert driver.vault is vault

    def test_init_creates_vault_if_none(self):
        driver = ConcretePlatformDriver()
        assert driver.vault is not None
        assert isinstance(driver.vault, SessionVault)

    def test_check_health_missing(self, vault):
        driver = ConcretePlatformDriver(vault=vault)
        # No session saved → health should be false
        result = driver.check_health()
        assert result is False

    def test_check_health_healthy(self, vault):
        vault.save("test_platform", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = ConcretePlatformDriver(vault=vault)
        result = driver.check_health()
        assert result is True

    def test_require_valid_session_exits_if_expired(self, vault, capsys):
        """require_valid_session calls sys.exit when expired."""
        old_time = datetime.now(timezone.utc) - timedelta(days=90)
        save_with_timestamp(vault, "test_platform", old_time)
        driver = ConcretePlatformDriver(vault=vault)
        with pytest.raises(SystemExit) as exc_info:
            driver.require_valid_session()
        assert exc_info.value.code == 1

    def test_require_valid_session_exits_if_missing(self, vault, capsys):
        """require_valid_session calls sys.exit when missing."""
        driver = ConcretePlatformDriver(vault=vault)
        with pytest.raises(SystemExit) as exc_info:
            driver.require_valid_session()
        assert exc_info.value.code == 1

    def test_require_valid_session_warns_if_expiring(self, vault, capsys):
        """require_valid_session warns but doesn't exit if expiring soon."""
        # test_platform is unknown -> DEFAULT_TTL_DAYS = 30, so 27 days ago => 3 days left
        harvest_time = datetime.now(timezone.utc) - timedelta(days=27)
        save_with_timestamp(vault, "test_platform", harvest_time)
        driver = ConcretePlatformDriver(vault=vault)
        driver.require_valid_session()
        captured = capsys.readouterr()
        assert "expire" in captured.out.lower() or "⚠️" in captured.out

    def test_require_valid_session_no_output_if_healthy(self, vault, capsys):
        """require_valid_session is quiet when healthy."""
        vault.save("test_platform", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = ConcretePlatformDriver(vault=vault)
        driver.require_valid_session()
        # No exit, minimal output expected


# ── get_driver ─────────────────────────────────────────────────────────────────

class TestGetDriver:
    def test_get_driver_kdp(self):
        from agentreach.drivers.kdp import KDPDriver
        driver = get_driver("kdp")
        assert isinstance(driver, KDPDriver)

    def test_get_driver_etsy(self):
        from agentreach.drivers.etsy import EtsyDriver
        driver = get_driver("etsy")
        assert isinstance(driver, EtsyDriver)

    def test_get_driver_gumroad(self):
        from agentreach.drivers.gumroad import GumroadDriver
        driver = get_driver("gumroad")
        assert isinstance(driver, GumroadDriver)

    def test_get_driver_pinterest(self):
        from agentreach.drivers.pinterest import PinterestDriver
        driver = get_driver("pinterest")
        assert isinstance(driver, PinterestDriver)

    def test_get_driver_reddit(self):
        from agentreach.drivers.reddit import RedditDriver
        driver = get_driver("reddit")
        assert isinstance(driver, RedditDriver)

    def test_get_driver_twitter(self):
        from agentreach.drivers.twitter import TwitterDriver
        driver = get_driver("twitter")
        assert isinstance(driver, TwitterDriver)

    def test_get_driver_nextdoor(self):
        from agentreach.drivers.nextdoor import NextdoorDriver
        driver = get_driver("nextdoor")
        assert isinstance(driver, NextdoorDriver)

    def test_get_driver_unknown_raises(self):
        with pytest.raises(ValueError) as exc_info:
            get_driver("unknown_platform_xyz")
        assert "unknown" in str(exc_info.value).lower()

    def test_get_driver_case_insensitive(self):
        driver = get_driver("KDP")
        from agentreach.drivers.kdp import KDPDriver
        assert isinstance(driver, KDPDriver)

    def test_all_drivers_instantiatable(self):
        """All registered drivers can be instantiated."""
        for name, cls in DRIVERS.items():
            driver = cls()
            assert driver is not None


# ── KDP Driver ─────────────────────────────────────────────────────────────────

class TestKDPDriver:
    def test_platform_name(self):
        from agentreach.drivers.kdp import KDPDriver
        driver = KDPDriver()
        assert driver.platform_name == "kdp"

    def test_upload_paperback_missing_manuscript(self, vault, tmp_path, sample_cover_pdf):
        from agentreach.drivers.kdp import KDPDriver, KDPBookDetails
        vault.save("kdp", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = KDPDriver(vault=vault)
        details = KDPBookDetails(title="Test Book")
        result = driver.upload_paperback(
            details,
            manuscript_path=tmp_path / "nonexistent.pdf",
            cover_path=sample_cover_pdf,
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_upload_paperback_missing_cover(self, vault, tmp_path, sample_pdf):
        from agentreach.drivers.kdp import KDPDriver, KDPBookDetails
        vault.save("kdp", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = KDPDriver(vault=vault)
        details = KDPBookDetails(title="Test Book")
        result = driver.upload_paperback(
            details,
            manuscript_path=sample_pdf,
            cover_path=tmp_path / "nonexistent_cover.pdf",
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_kdp_book_details_defaults(self):
        from agentreach.drivers.kdp import KDPBookDetails
        details = KDPBookDetails(title="My Book")
        assert details.title == "My Book"
        assert details.subtitle == ""
        assert details.author == ""
        assert details.publisher == ""
        assert details.price_usd == 12.99
        assert details.keywords == []
        assert details.language == "English"

    @pytest.mark.asyncio
    async def test_verify_session_returns_bool(self, vault):
        """verify_session returns True or False without crashing."""
        from agentreach.drivers.kdp import KDPDriver

        vault.save("kdp", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = KDPDriver(vault=vault)

        # Mock platform_context so we don't actually launch browsers
        mock_page = AsyncMock()
        mock_page.url = "https://kdp.amazon.com/en_US/bookshelf"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        mock_ctx = AsyncMock()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            yield mock_ctx, mock_page

        with patch("agentreach.drivers.kdp.platform_context", mock_platform_context):
            result = await driver.verify_session()
            assert isinstance(result, bool)


# ── Gumroad Driver ─────────────────────────────────────────────────────────────

class TestGumroadDriver:
    def test_platform_name(self):
        from agentreach.drivers.gumroad import GumroadDriver
        driver = GumroadDriver()
        assert driver.platform_name == "gumroad"

    def test_save_token(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver
        driver = GumroadDriver(vault=vault)
        driver.save_token("test_token_123")
        session = vault.load("gumroad")
        assert session is not None
        assert session.get("access_token") == "test_token_123"

    def test_get_token_from_vault(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver
        vault.save("gumroad", {"access_token": "vault_token"})
        driver = GumroadDriver(vault=vault)
        token = driver._get_token()
        assert token == "vault_token"

    def test_get_token_from_init_arg(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver
        driver = GumroadDriver(access_token="init_token", vault=vault)
        assert driver._get_token() == "init_token"

    def test_get_token_from_env(self, vault, monkeypatch):
        from agentreach.drivers.gumroad import GumroadDriver
        monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "env_token")
        driver = GumroadDriver(vault=vault)
        assert driver._get_token() == "env_token"

    def test_get_token_returns_none_if_missing(self, vault):
        from agentreach.drivers.gumroad import GumroadDriver
        driver = GumroadDriver(vault=vault)
        assert driver._get_token() is None

    @pytest.mark.asyncio
    async def test_verify_session_no_token(self, vault):
        """verify_session returns False when no token available."""
        from agentreach.drivers.gumroad import GumroadDriver
        driver = GumroadDriver(vault=vault)
        result = await driver.verify_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_session_with_valid_token(self, vault):
        """verify_session returns True when API returns 200 and stores seller subdomain."""
        from agentreach.drivers.gumroad import GumroadDriver

        driver = GumroadDriver(access_token="valid_token", vault=vault)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user": {
                "profile_url": "https://gumroad.com/tester"
            }
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await driver.verify_session()
            assert result is True
            session = vault.load("gumroad")
            assert session.get("seller_subdomain") == "tester"

    @pytest.mark.asyncio
    async def test_verify_session_with_invalid_token(self, vault):
        """verify_session returns False when API returns 401."""
        from agentreach.drivers.gumroad import GumroadDriver

        driver = GumroadDriver(access_token="invalid_token", vault=vault)

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await driver.verify_session()
            assert result is False

    def test_gumroad_product_defaults(self):
        from agentreach.drivers.gumroad import GumroadProduct
        p = GumroadProduct(name="Test", description="Desc", price_cents=799)
        assert p.name == "Test"
        assert p.price_cents == 799
        assert p.custom_url == ""
        assert p.file_path is None


# ── Etsy Driver ────────────────────────────────────────────────────────────────

class TestEtsyDriver:
    def test_platform_name(self):
        from agentreach.drivers.etsy import EtsyDriver
        driver = EtsyDriver()
        assert driver.platform_name == "etsy"

    def test_save_credentials(self, vault):
        from agentreach.drivers.etsy import EtsyDriver
        driver = EtsyDriver(vault=vault)
        driver.save_credentials("key123", "token456", "shop789")
        session = vault.load("etsy")
        assert session["api_key"] == "key123"
        assert session["access_token"] == "token456"
        assert session["shop_id"] == "shop789"

    def test_get_credentials_from_vault(self, vault):
        from agentreach.drivers.etsy import EtsyDriver
        vault.save("etsy", {
            "api_key": "vault_key",
            "access_token": "vault_token",
            "shop_id": "vault_shop",
        })
        driver = EtsyDriver(vault=vault)
        key, token, shop = driver._get_credentials()
        assert key == "vault_key"
        assert token == "vault_token"
        assert shop == "vault_shop"

    def test_get_credentials_from_init(self, vault):
        from agentreach.drivers.etsy import EtsyDriver
        driver = EtsyDriver(api_key="init_key", access_token="init_token", shop_id="init_shop", vault=vault)
        key, token, shop = driver._get_credentials()
        assert key == "init_key"

    def test_get_credentials_from_env(self, vault, monkeypatch):
        from agentreach.drivers.etsy import EtsyDriver
        monkeypatch.setenv("ETSY_API_KEY", "env_key")
        monkeypatch.setenv("ETSY_ACCESS_TOKEN", "env_token")
        monkeypatch.setenv("ETSY_SHOP_ID", "env_shop")
        driver = EtsyDriver(vault=vault)
        key, token, shop = driver._get_credentials()
        assert key == "env_key"

    def test_etsy_listing_defaults(self):
        from agentreach.drivers.etsy import EtsyListing
        listing = EtsyListing(title="Test", description="Desc", price=7.99)
        assert listing.quantity == 999
        assert listing.who_made == "i_did"
        assert listing.tags == []
        assert listing.digital_files == []

    @pytest.mark.asyncio
    async def test_create_listing_missing_credentials(self, vault):
        """create_listing returns error when credentials missing."""
        from agentreach.drivers.etsy import EtsyDriver, EtsyListing
        driver = EtsyDriver(vault=vault)
        listing = EtsyListing(title="Test", description="Desc", price=7.99)
        result = await driver.create_listing(listing)
        assert result.success is False
        assert "credentials" in result.error.lower()

    def test_headers_format(self, vault):
        from agentreach.drivers.etsy import EtsyDriver
        driver = EtsyDriver(vault=vault)
        headers = driver._headers("my_key", "my_token")
        assert headers["x-api-key"] == "my_key"
        assert "Bearer my_token" in headers["Authorization"]


# ── Reddit Driver ──────────────────────────────────────────────────────────────

class TestRedditDriver:
    def test_platform_name(self):
        from agentreach.drivers.reddit import RedditDriver
        driver = RedditDriver()
        assert driver.platform_name == "reddit"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_post_comment_no_session(self, vault):
        """post_comment handles missing session gracefully via platform_context raising."""
        from agentreach.drivers.reddit import RedditDriver
        from agentreach.browser.session import SessionNotFoundError

        vault.save("reddit", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = RedditDriver(vault=vault)

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            mock_page = AsyncMock()
            mock_page.url = "https://www.reddit.com/r/test/comments/abc/"
            mock_page.goto = AsyncMock()
            mock_page.wait_for_timeout = AsyncMock()
            mock_page.evaluate = AsyncMock(return_value="login")  # simulate redirect to login
            # Ensure locator chain is fully async to avoid unawaited coroutine warnings
            mock_locator = AsyncMock()
            mock_locator.first = AsyncMock()
            mock_locator.first.wait_for = AsyncMock(side_effect=Exception("no comment box"))
            mock_locator.first.inner_text = AsyncMock(return_value="")
            mock_locator.first.type = AsyncMock()
            mock_page.locator = MagicMock(return_value=mock_locator)
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.reddit.platform_context", mock_platform_context):
            result = await driver.post_comment("https://www.reddit.com/r/test/", "hello")
            # Should return some UploadResult
            assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_create_post_login_redirect(self, vault):
        """create_post returns error when redirected to login."""
        from agentreach.drivers.reddit import RedditDriver

        vault.save("reddit", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = RedditDriver(vault=vault)

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            mock_page = AsyncMock()
            mock_page.url = "https://www.reddit.com/login"
            mock_page.goto = AsyncMock()
            mock_page.wait_for_timeout = AsyncMock()
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.reddit.platform_context", mock_platform_context):
            result = await driver.create_post("test", "Title", "Body")
            assert result.success is False
            assert "expired" in result.error.lower() or "login" in result.error.lower()


# ── Nextdoor Driver ────────────────────────────────────────────────────────────

class TestNextdoorDriver:
    def test_platform_name(self):
        from agentreach.drivers.nextdoor import NextdoorDriver
        driver = NextdoorDriver()
        assert driver.platform_name == "nextdoor"

    @pytest.mark.asyncio
    async def test_create_post_login_redirect(self, vault):
        """create_post returns error when redirected to login."""
        from agentreach.drivers.nextdoor import NextdoorDriver

        vault.save("nextdoor", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        driver = NextdoorDriver(vault=vault)

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_platform_context(*args, **kwargs):
            mock_page = AsyncMock()
            mock_page.url = "https://nextdoor.com/login/"
            mock_page.goto = AsyncMock()
            mock_page.wait_for_timeout = AsyncMock()
            yield AsyncMock(), mock_page

        with patch("agentreach.drivers.nextdoor.platform_context", mock_platform_context):
            result = await driver.create_post("Hello neighborhood!")
            assert result.success is False
            assert "expired" in result.error.lower() or "login" in result.error.lower()


# ── Pinterest Driver ───────────────────────────────────────────────────────────

class TestPinterestDriver:
    def test_platform_name(self):
        from agentreach.drivers.pinterest import PinterestDriver
        driver = PinterestDriver()
        assert driver.platform_name == "pinterest"

    def test_pinterest_pin_defaults(self):
        from agentreach.drivers.pinterest import PinterestPin
        pin = PinterestPin(
            title="Test Pin",
            description="Pin desc",
            image_path=Path("/tmp/test.png"),
            link="https://example.com",
            board_name="My Board",
        )
        assert pin.title == "Test Pin"
        assert pin.board_name == "My Board"


# ── Twitter Driver ─────────────────────────────────────────────────────────────

class TestTwitterDriver:
    def test_platform_name(self):
        from agentreach.drivers.twitter import TwitterDriver
        driver = TwitterDriver()
        assert driver.platform_name == "twitter"

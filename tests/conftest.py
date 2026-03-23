"""
AgentReach Test Suite — Shared Fixtures & Configuration
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agentreach.vault.store import SessionVault


# ── Vault Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def vault_dir(tmp_path):
    """Fresh temporary vault directory for each test."""
    return tmp_path / "vault"


@pytest.fixture
def vault(vault_dir):
    """A SessionVault pointed at a temp directory."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    return SessionVault(vault_dir=vault_dir)


@pytest.fixture
def vault_with_kdp(vault):
    """Vault pre-loaded with a healthy KDP session."""
    vault.save("kdp", {
        "platform": "kdp",
        "cookies": [{"name": "session", "value": "abc123", "domain": ".amazon.com"}],
        "storage_state": {"cookies": [], "origins": []},
    })
    return vault


@pytest.fixture
def vault_with_expired_kdp(vault):
    """Vault pre-loaded with an expired KDP session (harvested 60 days ago)."""
    old_time = datetime.now(timezone.utc) - timedelta(days=60)
    vault.save("kdp", {
        "platform": "kdp",
        "_saved_at": old_time.isoformat(),
        "cookies": [{"name": "session", "value": "old123", "domain": ".amazon.com"}],
    })
    return vault


@pytest.fixture
def vault_with_expiring_kdp(vault):
    """Vault pre-loaded with a soon-to-expire KDP session (harvested 27 days ago → 3 days left)."""
    harvest_time = datetime.now(timezone.utc) - timedelta(days=27)
    vault.save("kdp", {
        "platform": "kdp",
        "_saved_at": harvest_time.isoformat(),
        "cookies": [{"name": "session", "value": "expiring123", "domain": ".amazon.com"}],
    })
    return vault


@pytest.fixture
def session_data_factory():
    """Factory for creating session data dicts."""
    def _make(platform="kdp", days_ago=1, extra=None):
        harvest_time = datetime.now(timezone.utc) - timedelta(days=days_ago)
        data = {
            "platform": platform,
            "_saved_at": harvest_time.isoformat(),
            "cookies": [{"name": "session", "value": "test_token", "domain": f".{platform}.com"}],
            "storage_state": {"cookies": [], "origins": []},
        }
        if extra:
            data.update(extra)
        return data
    return _make


# ── CLI Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    from typer.testing import CliRunner
    return CliRunner()


@pytest.fixture
def cli_app():
    """The main CLI app."""
    from agentreach.cli import app
    return app


# ── Browser/Driver Mock Fixtures ───────────────────────────────────────────────

@pytest.fixture
def mock_page():
    """A mock Playwright Page object."""
    page = AsyncMock()
    page.url = "https://example.com"
    page.goto = AsyncMock(return_value=None)
    page.wait_for_timeout = AsyncMock(return_value=None)
    page.wait_for_url = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock(return_value=None)
    page.evaluate = AsyncMock(return_value=None)
    page.content = AsyncMock(return_value="<html></html>")
    page.locator = MagicMock(return_value=AsyncMock())
    page.query_selector_all = AsyncMock(return_value=[])
    page.click = AsyncMock(return_value=None)
    page.keyboard = AsyncMock()
    return page


@pytest.fixture
def mock_context():
    """A mock Playwright BrowserContext."""
    ctx = AsyncMock()
    ctx.cookies = AsyncMock(return_value=[
        {"name": "session", "value": "mock_token", "domain": ".amazon.com"}
    ])
    ctx.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})
    ctx.add_cookies = AsyncMock(return_value=None)
    ctx.new_page = AsyncMock()
    return ctx


@pytest.fixture
def mock_browser():
    """A mock Playwright Browser."""
    browser = AsyncMock()
    browser.close = AsyncMock(return_value=None)
    return browser


# ── Platform Session Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def all_platforms():
    """List of all supported platform names."""
    return ["kdp", "etsy", "gumroad", "pinterest", "reddit", "twitter", "nextdoor"]


@pytest.fixture
def vault_all_platforms(vault, all_platforms, session_data_factory):
    """Vault pre-loaded with healthy sessions for all platforms."""
    for platform in all_platforms:
        vault.save(platform, session_data_factory(platform=platform))
    return vault


# ── File Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf(tmp_path):
    """A fake PDF file for upload testing."""
    pdf_path = tmp_path / "test_manuscript.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake pdf content\n")
    return pdf_path


@pytest.fixture
def sample_cover_pdf(tmp_path):
    """A fake cover PDF for upload testing."""
    cover_path = tmp_path / "test_cover.pdf"
    cover_path.write_bytes(b"%PDF-1.4\n% fake cover content\n")
    return cover_path


@pytest.fixture
def sample_image(tmp_path):
    """A fake PNG image file for upload testing."""
    img_path = tmp_path / "test_image.png"
    # Minimal valid PNG header
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return img_path

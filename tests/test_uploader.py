"""
Tests for AgentReach Uploader — file upload strategies, MIME type detection, error responses
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agentreach.browser.uploader import (
    upload_file,
    wait_for_upload_complete,
    _file_registered,
)


# ── upload_file ────────────────────────────────────────────────────────────────

class TestUploadFile:
    @pytest.mark.asyncio
    async def test_raises_if_file_not_found(self, tmp_path):
        """upload_file raises FileNotFoundError for missing file."""
        mock_page = AsyncMock()
        missing = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            await upload_file(mock_page, missing)
        assert "not found" in str(exc_info.value).lower() or "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_strategy1_direct_set_input_files(self, sample_pdf):
        """Strategy 1: direct setInputFiles succeeds if file is registered."""
        mock_page = AsyncMock()

        # Mock the locator and its set_input_files
        mock_locator = AsyncMock()
        mock_locator.first = AsyncMock()
        mock_locator.first.set_input_files = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value=f"<html>{sample_pdf.name}</html>")

        result = await upload_file(mock_page, sample_pdf)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_all_strategies_fail(self, sample_pdf):
        """Returns False when all upload strategies fail."""
        mock_page = AsyncMock()

        # All strategies raise exceptions
        mock_locator = AsyncMock()
        mock_locator.first = AsyncMock()
        mock_locator.first.set_input_files = AsyncMock(side_effect=Exception("Strategy 1 failed"))
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.evaluate = AsyncMock(side_effect=Exception("Strategy 2 failed"))
        mock_page.click = AsyncMock(side_effect=Exception("Strategy 3 failed"))

        result = await upload_file(mock_page, sample_pdf)
        assert result is False

    @pytest.mark.asyncio
    async def test_file_path_converted_to_path(self, sample_pdf):
        """upload_file accepts string path as well as Path."""
        mock_page = AsyncMock()
        mock_locator = AsyncMock()
        mock_locator.first = AsyncMock()
        mock_locator.first.set_input_files = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value=f"<html>{sample_pdf.name}</html>")

        # Should work with string
        result = await upload_file(mock_page, str(sample_pdf))
        assert result is True

    @pytest.mark.asyncio
    async def test_strategy3_file_chooser(self, sample_pdf):
        """Strategy 3: file chooser interception with trigger_selector."""
        mock_page = AsyncMock()
        mock_file_chooser = AsyncMock()
        mock_file_chooser.set_files = AsyncMock()

        # Strategy 1 and 2 fail
        mock_locator = AsyncMock()
        mock_locator.first = AsyncMock()
        mock_locator.first.set_input_files = AsyncMock(side_effect=Exception("fail"))
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.evaluate = AsyncMock(side_effect=Exception("fail"))

        # Strategy 3 succeeds via file chooser
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_expect_file_chooser(*args, **kwargs):
            info = MagicMock()
            info.value = AsyncMock(return_value=mock_file_chooser)()
            yield info

        mock_page.expect_file_chooser = mock_expect_file_chooser
        mock_page.click = AsyncMock()

        result = await upload_file(
            mock_page,
            sample_pdf,
            trigger_selector='button[data-action="upload"]',
        )
        assert result is True
        mock_file_chooser.set_files.assert_called_once_with(str(sample_pdf))


# ── _file_registered ───────────────────────────────────────────────────────────

class TestFileRegistered:
    @pytest.mark.asyncio
    async def test_returns_true_when_files_present(self):
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=1)
        result = await _file_registered(mock_page, 'input[type="file"]')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_files(self):
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=0)
        result = await _file_registered(mock_page, 'input[type="file"]')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS error"))
        result = await _file_registered(mock_page, 'input[type="file"]')
        assert result is False


# ── wait_for_upload_complete ───────────────────────────────────────────────────

class TestWaitForUploadComplete:
    @pytest.mark.asyncio
    async def test_waits_for_custom_indicator(self):
        """Waits for custom success indicator selector."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        result = await wait_for_upload_complete(
            mock_page,
            success_indicator=".upload-success",
        )
        assert result is True
        mock_page.wait_for_selector.assert_called_once_with(
            ".upload-success", timeout=60000
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_selector_timeout(self):
        """Returns False when success indicator times out."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.wait_for_timeout = AsyncMock()

        result = await wait_for_upload_complete(
            mock_page,
            success_indicator=".upload-success",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_generic_wait_no_indicator(self):
        """With no indicator and no progress element found, returns False (cannot confirm)."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("not found"))
        mock_page.wait_for_timeout = AsyncMock()

        result = await wait_for_upload_complete(mock_page)
        # Cannot confirm completion without any indicator — returns False honestly
        assert result is False

    @pytest.mark.asyncio
    async def test_custom_timeout_passed_to_selector(self):
        """Custom timeout is respected."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        await wait_for_upload_complete(
            mock_page,
            success_indicator=".done",
            timeout=30000,
        )
        mock_page.wait_for_selector.assert_called_once_with(".done", timeout=30000)

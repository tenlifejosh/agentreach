"""
Tests for AgentReach CLI — top-level commands, flags, subcommands, and error cases
"""

import base64
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from agentreach.cli import app
from agentreach.vault.health import SessionHealth, SessionStatus
from agentreach.drivers.base import UploadResult


@pytest.fixture
def runner():
    return CliRunner()


def _health(platform: str, status: SessionStatus, days_remaining=None):
    return SessionHealth(
        platform=platform,
        status=status,
        harvested_at=None,
        estimated_expiry=None,
        days_remaining=days_remaining,
        message="",
    )


# ── Version ───────────────────────────────────────────────────────────────────

class TestVersionCommand:
    def test_version_command(self, runner):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "AgentReach" in result.output

    def test_version_flag(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "AgentReach" in result.output

    def test_version_short_flag(self, runner):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "AgentReach" in result.output


# ── Status / Doctor / Platforms ───────────────────────────────────────────────

class TestStatusCommand:
    def test_status_runs_without_error(self, runner):
        with patch("agentreach.vault.health.check_all", return_value=[]):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0

    def test_status_outputs_platform_rows(self, runner):
        results = [
            _health("kdp", SessionStatus.HEALTHY, 20),
            _health("etsy", SessionStatus.MISSING),
        ]
        with patch("agentreach.vault.health.check_all", return_value=results):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "Amazon KDP" in result.output
            assert "Etsy" in result.output


class TestDoctorCommand:
    def test_doctor_runs(self, runner):
        with patch("agentreach.vault.health.check_all", return_value=[]):
            with patch("agentreach.drivers.get_driver", return_value=MagicMock()):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(stdout="1.40.0", returncode=0)
                    result = runner.invoke(app, ["doctor"])
                    assert result.exit_code == 0
                    assert "Doctor" in result.output

    def test_doctor_shows_version(self, runner):
        from agentreach import __version__
        with patch("agentreach.vault.health.check_all", return_value=[]):
            with patch("agentreach.drivers.get_driver", return_value=MagicMock()):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(stdout="1.40.0", returncode=0)
                    result = runner.invoke(app, ["doctor"])
                    assert __version__ in result.output


class TestPlatformsCommand:
    def test_platforms_command_runs(self, runner):
        with patch("agentreach.vault.health.check_session", return_value=_health("kdp", SessionStatus.MISSING)):
            result = runner.invoke(app, ["platforms"])
            assert result.exit_code == 0

    def test_platforms_shows_known_platforms(self, runner):
        with patch("agentreach.vault.health.check_session", return_value=_health("kdp", SessionStatus.MISSING)):
            result = runner.invoke(app, ["platforms"])
            assert "Amazon KDP" in result.output
            assert "Nextdoor" in result.output


# ── Harvest / Verify ──────────────────────────────────────────────────────────

class TestHarvestCommand:
    def test_harvest_calls_harvester(self, runner):
        with patch("agentreach.browser.harvester.harvest") as mock_harvest:
            result = runner.invoke(app, ["harvest", "kdp"])
            assert result.exit_code == 0
            mock_harvest.assert_called_once_with("kdp", timeout=300)

    def test_harvest_with_timeout_flag(self, runner):
        with patch("agentreach.browser.harvester.harvest") as mock_harvest:
            result = runner.invoke(app, ["harvest", "kdp", "--timeout", "120"])
            assert result.exit_code == 0
            mock_harvest.assert_called_once_with("kdp", timeout=120)


class TestVerifyCommand:
    def test_verify_valid_session(self, runner):
        mock_driver = MagicMock()
        mock_driver.verify_session = AsyncMock(return_value=True)
        with patch("agentreach.drivers.get_driver", return_value=mock_driver):
            result = runner.invoke(app, ["verify", "kdp"])
            assert result.exit_code == 0
            assert "valid" in result.output.lower()

    def test_verify_invalid_session(self, runner):
        mock_driver = MagicMock()
        mock_driver.verify_session = AsyncMock(return_value=False)
        with patch("agentreach.drivers.get_driver", return_value=mock_driver):
            result = runner.invoke(app, ["verify", "kdp"])
            assert result.exit_code == 0
            assert "invalid" in result.output.lower() or "expired" in result.output.lower()

    def test_verify_unknown_platform(self, runner):
        with patch("agentreach.drivers.get_driver", side_effect=ValueError("Unknown platform")):
            result = runner.invoke(app, ["verify", "nope"])
            assert result.exit_code != 0


# ── Backup / Restore ──────────────────────────────────────────────────────────

class TestBackupCommand:
    def test_backup_no_sessions(self, runner, tmp_path):
        with patch("agentreach.vault.store.VAULT_DIR", tmp_path):
            result = runner.invoke(app, ["backup"])
            assert result.exit_code == 0
            assert "Nothing to backup" in result.output or "No vault sessions" in result.output

    def test_backup_creates_file(self, runner, tmp_path):
        from agentreach.vault.store import SessionVault

        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        SessionVault(vault_dir=vault_dir).save("kdp", {"test": "data"})
        output_file = tmp_path / "test_backup.enc"

        with patch("agentreach.vault.store.VAULT_DIR", vault_dir):
            result = runner.invoke(app, ["backup", "--output", str(output_file)])
            assert result.exit_code == 0
            assert output_file.exists()


class TestRestoreCommand:
    def test_restore_missing_file(self, runner, tmp_path):
        missing_path = tmp_path / "nonexistent.enc"
        result = runner.invoke(app, ["restore", str(missing_path)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_restore_invalid_file_errors(self, runner, tmp_path):
        bad_file = tmp_path / "bad.enc"
        bad_file.write_bytes(b"not_valid_data")
        result = runner.invoke(app, ["restore", str(bad_file)])
        assert result.exit_code != 0
        assert "failed to decrypt" in result.output.lower() or "❌" in result.output

    def test_restore_valid_backup(self, runner, tmp_path):
        from agentreach.vault.store import SessionVault, _FERNET

        source_vault = tmp_path / "source_vault"
        source_vault.mkdir()
        SessionVault(vault_dir=source_vault).save("kdp", {"test": "restore_me"})

        bundle = {
            vf.name: base64.b64encode(vf.read_bytes()).decode()
            for vf in source_vault.glob("*.vault")
        }
        backup_path = tmp_path / "backup.enc"
        backup_path.write_bytes(_FERNET.encrypt(json.dumps(bundle).encode()))

        restore_vault = tmp_path / "restore_vault"
        restore_vault.mkdir()
        with patch("agentreach.vault.store.VAULT_DIR", restore_vault):
            result = runner.invoke(app, ["restore", str(backup_path)])
            assert result.exit_code == 0
            assert (restore_vault / "kdp.vault").exists()


# ── KDP / Gumroad / Reddit / Nextdoor Subcommands ─────────────────────────────

class TestKDPCommands:
    def test_kdp_upload_missing_files(self, runner):
        result = runner.invoke(app, [
            "kdp", "upload",
            "--manuscript", "/nope/missing.pdf",
            "--cover", "/nope/cover.pdf",
            "--title", "Test Book",
        ])
        assert result.exit_code != 0


class TestGumroadCommands:
    def test_gumroad_set_token(self, runner):
        mock_driver = MagicMock()
        with patch("agentreach.drivers.gumroad.GumroadDriver", return_value=mock_driver):
            result = runner.invoke(app, ["gumroad", "set-token", "my_token_123"])
            assert result.exit_code == 0
            mock_driver.save_token.assert_called_once_with("my_token_123")


class TestRedditCommands:
    def test_reddit_comment_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.comment = MagicMock(return_value=UploadResult(success=True, platform="reddit", message="Comment posted"))

        with patch("agentreach.drivers.reddit.RedditDriver", return_value=mock_driver):
            result = runner.invoke(app, ["reddit", "comment", "https://reddit.com/r/test", "hello"])
            assert result.exit_code == 0

    def test_reddit_comment_failure(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.comment = MagicMock(return_value=UploadResult(success=False, platform="reddit", error="Session expired"))

        with patch("agentreach.drivers.reddit.RedditDriver", return_value=mock_driver):
            result = runner.invoke(app, ["reddit", "comment", "https://reddit.com/r/test", "hello"])
            assert result.exit_code != 0


class TestNextdoorCommands:
    def test_nextdoor_post_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post = MagicMock(return_value=UploadResult(success=True, platform="nextdoor", message="Post published", url="https://nextdoor.com/post/1"))

        with patch("agentreach.drivers.nextdoor.NextdoorDriver", return_value=mock_driver):
            result = runner.invoke(app, ["nextdoor", "post", "Hello neighborhood!"])
            assert result.exit_code == 0

    def test_nextdoor_post_failure(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post = MagicMock(return_value=UploadResult(success=False, platform="nextdoor", error="failed"))

        with patch("agentreach.drivers.nextdoor.NextdoorDriver", return_value=mock_driver):
            result = runner.invoke(app, ["nextdoor", "post", "Hello neighborhood!"])
            assert result.exit_code != 0


class TestAdditionalCliCommands:
    def test_kdp_bookshelf_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.get_bookshelf = AsyncMock(return_value=[{"title": "Book A", "status": "LIVE"}])

        with patch("agentreach.drivers.kdp.KDPDriver", return_value=mock_driver):
            result = runner.invoke(app, ["kdp", "bookshelf"])
            assert result.exit_code == 0
            assert "Book A" in result.output

    def test_gumroad_publish_success(self, runner, sample_pdf):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.publish_product = MagicMock(return_value=UploadResult(success=True, platform="gumroad", message="Published", url="https://gumroad.com/l/test"))

        with patch("agentreach.drivers.gumroad.GumroadDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "gumroad", "publish",
                "--name", "Test Product",
                "--description", "Desc",
                "--price", "7.99",
                "--file", str(sample_pdf),
            ])
            assert result.exit_code == 0
            assert "Published" in result.output

    def test_gumroad_publish_failure(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.publish_product = MagicMock(return_value=UploadResult(success=False, platform="gumroad", error="bad publish"))

        with patch("agentreach.drivers.gumroad.GumroadDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "gumroad", "publish",
                "--name", "Test Product",
                "--description", "Desc",
                "--price", "7.99",
            ])
            assert result.exit_code != 0

    def test_gumroad_sales_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.check_sales = MagicMock(return_value={"sales": [{"price": 799, "product_name": "Guide", "created_at": "2026-03-23"}]})

        with patch("agentreach.drivers.gumroad.GumroadDriver", return_value=mock_driver):
            result = runner.invoke(app, ["gumroad", "sales"])
            assert result.exit_code == 0
            assert "Total sales found: 1" in result.output

    def test_etsy_set_credentials_success(self, runner):
        mock_driver = MagicMock()
        with patch("agentreach.drivers.etsy.EtsyDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "etsy", "set-credentials",
                "--api-key", "key",
                "--access-token", "token",
                "--shop-id", "shop123",
            ])
            assert result.exit_code == 0
            mock_driver.save_credentials.assert_called_once_with("key", "token", "shop123")

    def test_etsy_publish_success(self, runner, sample_pdf, sample_image):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.publish_listing = MagicMock(return_value=UploadResult(success=True, platform="etsy", message="Listing published"))

        with patch("agentreach.drivers.etsy.EtsyDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "etsy", "publish",
                "--title", "Test Listing",
                "--description", "Desc",
                "--price", "7.99",
                "--digital-file", str(sample_pdf),
                "--images", str(sample_image),
                "--tags", "printable,journal",
            ])
            assert result.exit_code == 0
            assert "Listing published" in result.output

    def test_etsy_publish_failure(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.publish_listing = MagicMock(return_value=UploadResult(success=False, platform="etsy", error="upload failed"))

        with patch("agentreach.drivers.etsy.EtsyDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "etsy", "publish",
                "--title", "Test Listing",
                "--description", "Desc",
                "--price", "7.99",
            ])
            assert result.exit_code != 0

    def test_pinterest_pin_success(self, runner, sample_image):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post_pin = MagicMock(return_value=UploadResult(success=True, platform="pinterest", message="Pin posted"))

        with patch("agentreach.drivers.pinterest.PinterestDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "pinterest", "pin",
                "--title", "Pin Title",
                "--description", "Pin Desc",
                "--image", str(sample_image),
                "--link", "https://example.com",
            ])
            assert result.exit_code == 0
            assert "Pin posted" in result.output

    def test_pinterest_pin_failure(self, runner, sample_image):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post_pin = MagicMock(return_value=UploadResult(success=False, platform="pinterest", error="Pin failed"))

        with patch("agentreach.drivers.pinterest.PinterestDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "pinterest", "pin",
                "--title", "Pin Title",
                "--description", "Pin Desc",
                "--image", str(sample_image),
            ])
            assert result.exit_code != 0

    def test_reddit_post_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post = MagicMock(return_value=UploadResult(success=True, platform="reddit", message="Post published", url="https://reddit.com/r/test/1"))

        with patch("agentreach.drivers.reddit.RedditDriver", return_value=mock_driver):
            result = runner.invoke(app, ["reddit", "post", "test", "Title", "Body"])
            assert result.exit_code == 0
            assert "Post published" in result.output

    def test_twitter_tweet_success(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.tweet = MagicMock(return_value=UploadResult(success=True, platform="twitter", message="Tweet posted"))

        with patch("agentreach.drivers.twitter.TwitterDriver", return_value=mock_driver):
            result = runner.invoke(app, ["twitter", "tweet", "hello world"])
            assert result.exit_code == 0
            assert "Tweet posted" in result.output

    def test_twitter_reply_failure(self, runner):
        mock_driver = MagicMock()
        mock_driver.require_valid_session = MagicMock()
        mock_driver.reply = MagicMock(return_value=UploadResult(success=False, platform="twitter", error="reply failed"))

        with patch("agentreach.drivers.twitter.TwitterDriver", return_value=mock_driver):
            result = runner.invoke(app, ["twitter", "reply", "https://x.com/test/1", "hi"])
            assert result.exit_code != 0

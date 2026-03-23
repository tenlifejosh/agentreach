"""
Tests for AgentReach CLI — all commands, flag parsing, error cases
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from typer.testing import CliRunner

from agentreach.cli import app


@pytest.fixture
def runner():
    return CliRunner()


# ── version command ────────────────────────────────────────────────────────────

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

    def test_version_contains_version_number(self, runner):
        result = runner.invoke(app, ["version"])
        from agentreach import __version__
        assert __version__ in result.output


# ── status command ─────────────────────────────────────────────────────────────

class TestStatusCommand:
    def test_status_runs_without_error(self, runner, tmp_path):
        """status command runs cleanly even with empty vault."""
        with patch("agentreach.cli.SessionVault") as MockVault:
            mock_vault = MagicMock()
            mock_vault.list_platforms.return_value = []
            MockVault.return_value = mock_vault

            with patch("agentreach.cli.check_all") as mock_check_all:
                mock_check_all.return_value = []
                result = runner.invoke(app, ["status"])
                assert result.exit_code == 0

    def test_status_shows_table(self, runner):
        """status command outputs table-like content."""
        from agentreach.vault.health import SessionHealth, SessionStatus
        mock_results = [
            SessionHealth(
                platform="kdp",
                status=SessionStatus.MISSING,
                harvested_at=None,
                estimated_expiry=None,
                days_remaining=None,
                message="No session found",
            )
        ]
        with patch("agentreach.cli.SessionVault"):
            with patch("agentreach.cli.check_all", return_value=mock_results):
                result = runner.invoke(app, ["status"])
                assert result.exit_code == 0
                # Should have some output
                assert len(result.output) > 0


# ── doctor command ─────────────────────────────────────────────────────────────

class TestDoctorCommand:
    def test_doctor_runs(self, runner):
        """doctor command runs without crashing."""
        from agentreach.vault.health import SessionHealth, SessionStatus
        mock_results = []
        with patch("agentreach.cli.SessionVault"):
            with patch("agentreach.cli.check_all", return_value=mock_results):
                with patch("agentreach.cli.get_driver") as mock_get_driver:
                    mock_driver = MagicMock()
                    mock_get_driver.return_value = mock_driver
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value = MagicMock(stdout="1.40.0", returncode=0)
                        result = runner.invoke(app, ["doctor"])
                        assert result.exit_code == 0

    def test_doctor_shows_version(self, runner):
        from agentreach.vault.health import SessionHealth, SessionStatus
        with patch("agentreach.cli.SessionVault"):
            with patch("agentreach.cli.check_all", return_value=[]):
                with patch("agentreach.cli.get_driver"):
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value = MagicMock(stdout="1.40.0", returncode=0)
                        result = runner.invoke(app, ["doctor"])
                        from agentreach import __version__
                        assert __version__ in result.output


# ── harvest command ────────────────────────────────────────────────────────────

class TestHarvestCommand:
    def test_harvest_calls_do_harvest(self, runner):
        """harvest command delegates to browser harvester."""
        with patch("agentreach.cli.do_harvest") as mock_harvest:
            result = runner.invoke(app, ["harvest", "kdp"])
            assert mock_harvest.called
            call_args = mock_harvest.call_args
            assert call_args[0][0] == "kdp"

    def test_harvest_with_timeout_flag(self, runner):
        with patch("agentreach.cli.do_harvest") as mock_harvest:
            result = runner.invoke(app, ["harvest", "kdp", "--timeout", "120"])
            assert mock_harvest.called
            call_kwargs = mock_harvest.call_args[1]
            assert call_kwargs.get("timeout") == 120

    def test_harvest_default_timeout(self, runner):
        with patch("agentreach.cli.do_harvest") as mock_harvest:
            result = runner.invoke(app, ["harvest", "etsy"])
            assert mock_harvest.called
            call_kwargs = mock_harvest.call_args[1]
            assert call_kwargs.get("timeout") == 300  # default

    def test_harvest_various_platforms(self, runner):
        platforms = ["kdp", "etsy", "gumroad", "pinterest", "reddit", "twitter"]
        for platform in platforms:
            with patch("agentreach.cli.do_harvest") as mock_harvest:
                result = runner.invoke(app, ["harvest", platform])
                assert mock_harvest.called, f"harvest not called for {platform}"


# ── verify command ─────────────────────────────────────────────────────────────

class TestVerifyCommand:
    def test_verify_valid_session(self, runner):
        """verify command succeeds when session is valid."""
        mock_driver = MagicMock()
        mock_driver.verify_session = AsyncMock(return_value=True)

        with patch("agentreach.cli.get_driver", return_value=mock_driver):
            result = runner.invoke(app, ["verify", "kdp"])
            assert result.exit_code == 0
            assert "valid" in result.output.lower() or "✅" in result.output

    def test_verify_invalid_session(self, runner):
        """verify command indicates invalid when session fails."""
        mock_driver = MagicMock()
        mock_driver.verify_session = AsyncMock(return_value=False)

        with patch("agentreach.cli.get_driver", return_value=mock_driver):
            result = runner.invoke(app, ["verify", "kdp"])
            assert result.exit_code == 0
            assert "invalid" in result.output.lower() or "❌" in result.output

    def test_verify_unknown_platform(self, runner):
        """verify with unknown platform should error gracefully."""
        with patch("agentreach.cli.get_driver", side_effect=ValueError("Unknown platform")):
            result = runner.invoke(app, ["verify", "unknown_platform_xyz"])
            # Should not crash the runner entirely
            assert result.exit_code != 0 or "unknown" in result.output.lower()


# ── platforms command ──────────────────────────────────────────────────────────

class TestPlatformsCommand:
    def test_platforms_command_runs(self, runner):
        with patch("agentreach.cli.SessionVault"):
            with patch("agentreach.cli.check_session") as mock_check:
                from agentreach.vault.health import SessionHealth, SessionStatus
                mock_check.return_value = SessionHealth(
                    platform="kdp",
                    status=SessionStatus.MISSING,
                    harvested_at=None,
                    estimated_expiry=None,
                    days_remaining=None,
                    message="",
                )
                result = runner.invoke(app, ["platforms"])
                assert result.exit_code == 0

    def test_platforms_shows_platform_names(self, runner):
        with patch("agentreach.cli.SessionVault"):
            with patch("agentreach.cli.check_session") as mock_check:
                from agentreach.vault.health import SessionHealth, SessionStatus
                mock_check.return_value = SessionHealth(
                    platform="kdp",
                    status=SessionStatus.MISSING,
                    harvested_at=None,
                    estimated_expiry=None,
                    days_remaining=None,
                    message="",
                )
                result = runner.invoke(app, ["platforms"])
                assert "KDP" in result.output or "kdp" in result.output.lower()


# ── backup command ─────────────────────────────────────────────────────────────

class TestBackupCommand:
    def test_backup_no_sessions(self, runner, tmp_path):
        """backup with empty vault gives warning."""
        with patch("agentreach.cli.VAULT_DIR", tmp_path):
            result = runner.invoke(app, ["backup"])
            assert "No vault sessions" in result.output or result.exit_code == 0

    def test_backup_creates_file(self, runner, tmp_path):
        """backup with sessions creates an encrypted file."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Pre-populate a vault file
        from agentreach.vault.store import SessionVault, _FERNET
        vault = SessionVault(vault_dir=vault_dir)
        vault.save("kdp", {"test": "data"})

        output_file = tmp_path / "test_backup.enc"

        with patch("agentreach.cli.VAULT_DIR", vault_dir):
            result = runner.invoke(app, ["backup", "--output", str(output_file)])
            assert output_file.exists()


# ── restore command ────────────────────────────────────────────────────────────

class TestRestoreCommand:
    def test_restore_missing_file(self, runner, tmp_path):
        """restore with non-existent file exits with error."""
        missing_path = tmp_path / "nonexistent.enc"
        result = runner.invoke(app, ["restore", str(missing_path)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "❌" in result.output

    def test_restore_invalid_file_errors(self, runner, tmp_path):
        """restore with invalid/corrupt file shows error."""
        bad_file = tmp_path / "bad.enc"
        bad_file.write_bytes(b"not_valid_data")
        result = runner.invoke(app, ["restore", str(bad_file)])
        assert result.exit_code != 0
        assert "❌" in result.output or "fail" in result.output.lower()

    def test_restore_valid_backup(self, runner, tmp_path):
        """restore from valid backup succeeds."""
        import json
        import base64
        from agentreach.vault.store import SessionVault, _FERNET, VAULT_DIR

        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        vault = SessionVault(vault_dir=vault_dir)
        vault.save("kdp", {"test": "restore_me"})

        # Create backup
        backup_path = tmp_path / "backup.enc"
        bundle = {}
        for vf in vault_dir.glob("*.vault"):
            bundle[vf.name] = base64.b64encode(vf.read_bytes()).decode()
        payload = json.dumps(bundle).encode()
        backup_path.write_bytes(_FERNET.encrypt(payload))

        with patch("agentreach.cli.VAULT_DIR", vault_dir):
            result = runner.invoke(app, ["restore", str(backup_path)])
            assert result.exit_code == 0


# ── KDP subcommands ────────────────────────────────────────────────────────────

class TestKDPCommands:
    def test_kdp_upload_missing_files(self, runner, tmp_path):
        """kdp upload errors when files don't exist."""
        from agentreach.drivers.kdp import KDPDriver
        mock_driver = MagicMock(spec=KDPDriver)
        mock_driver.require_valid_session = MagicMock()

        with patch("agentreach.cli.KDPDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "kdp", "upload",
                "--manuscript", str(tmp_path / "nonexistent.pdf"),
                "--cover", str(tmp_path / "nonexistent_cover.pdf"),
                "--title", "Test Book",
            ])
            # Should fail due to missing files
            assert result.exit_code != 0 or "not found" in result.output.lower()


# ── Gumroad subcommands ────────────────────────────────────────────────────────

class TestGumroadCommands:
    def test_gumroad_set_token(self, runner):
        """gumroad set-token saves token."""
        from agentreach.drivers.gumroad import GumroadDriver
        mock_driver = MagicMock(spec=GumroadDriver)
        mock_driver.save_token = MagicMock()

        with patch("agentreach.cli.GumroadDriver", return_value=mock_driver):
            result = runner.invoke(app, ["gumroad", "set-token", "my_token_123"])
            mock_driver.save_token.assert_called_once_with("my_token_123")


# ── Reddit subcommands ─────────────────────────────────────────────────────────

class TestRedditCommands:
    def test_reddit_comment_success(self, runner):
        from agentreach.drivers.reddit import RedditDriver
        from agentreach.drivers.base import UploadResult

        mock_driver = MagicMock(spec=RedditDriver)
        mock_driver.require_valid_session = MagicMock()
        mock_driver.comment = MagicMock(return_value=UploadResult(
            success=True,
            platform="reddit",
            message="Comment posted",
        ))

        with patch("agentreach.cli.RedditDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "reddit", "comment",
                "https://www.reddit.com/r/test/comments/abc/test",
                "My test comment",
            ])
            assert result.exit_code == 0

    def test_reddit_comment_failure(self, runner):
        from agentreach.drivers.reddit import RedditDriver
        from agentreach.drivers.base import UploadResult

        mock_driver = MagicMock(spec=RedditDriver)
        mock_driver.require_valid_session = MagicMock()
        mock_driver.comment = MagicMock(return_value=UploadResult(
            success=False,
            platform="reddit",
            error="Session expired",
        ))

        with patch("agentreach.cli.RedditDriver", return_value=mock_driver):
            result = runner.invoke(app, [
                "reddit", "comment",
                "https://www.reddit.com/r/test/comments/abc/test",
                "My test comment",
            ])
            assert result.exit_code != 0


# ── Nextdoor subcommands ───────────────────────────────────────────────────────

class TestNextdoorCommands:
    def test_nextdoor_post_success(self, runner):
        from agentreach.drivers.nextdoor import NextdoorDriver
        from agentreach.drivers.base import UploadResult

        mock_driver = MagicMock(spec=NextdoorDriver)
        mock_driver.require_valid_session = MagicMock()
        mock_driver.post = MagicMock(return_value=UploadResult(
            success=True,
            platform="nextdoor",
            url="https://nextdoor.com/post/123",
            message="Post published",
        ))

        with patch("agentreach.cli.NextdoorDriver", return_value=mock_driver):
            result = runner.invoke(app, ["nextdoor", "post", "Hello neighborhood!"])
            assert result.exit_code == 0

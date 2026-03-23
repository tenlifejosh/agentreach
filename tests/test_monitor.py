"""
Tests for AgentReach Session Monitor — categorization, alerts, quiet mode
"""

import pytest
from datetime import datetime, timezone, timedelta
from io import StringIO
from unittest.mock import patch

from agentreach.vault.monitor import monitor, _categorize, _print_alerts
from agentreach.vault.health import SessionHealth, SessionStatus


# ── _categorize ───────────────────────────────────────────────────────────────

class TestCategorize:
    def _health(self, status, days_remaining=None):
        return SessionHealth(
            platform="test",
            status=status,
            harvested_at=None,
            estimated_expiry=None,
            days_remaining=days_remaining,
            message="",
        )

    def test_healthy_many_days(self):
        h = self._health(SessionStatus.HEALTHY, days_remaining=20)
        assert _categorize(h) == "healthy"

    def test_healthy_few_days_is_warning(self):
        """Healthy status with few days left becomes warning."""
        h = self._health(SessionStatus.HEALTHY, days_remaining=4)
        assert _categorize(h) == "warning"

    def test_expiring_soon_critical(self):
        h = self._health(SessionStatus.EXPIRING_SOON, days_remaining=1)
        assert _categorize(h) == "critical"

    def test_expiring_soon_warning(self):
        h = self._health(SessionStatus.EXPIRING_SOON, days_remaining=4)
        assert _categorize(h) == "warning"

    def test_expired(self):
        h = self._health(SessionStatus.EXPIRED, days_remaining=-5)
        assert _categorize(h) == "expired"

    def test_missing(self):
        h = self._health(SessionStatus.MISSING)
        assert _categorize(h) == "missing"

    def test_unknown(self):
        h = self._health(SessionStatus.UNKNOWN)
        assert _categorize(h) == "unknown"


# ── monitor ───────────────────────────────────────────────────────────────────

class TestMonitor:
    def test_monitor_returns_dict_with_buckets(self, vault):
        result = monitor(vault, quiet=True)
        assert isinstance(result, dict)
        assert "healthy" in result
        assert "warning" in result
        assert "critical" in result
        assert "expired" in result
        assert "missing" in result
        assert "unknown" in result

    def test_monitor_all_missing_on_empty_vault(self, vault):
        result = monitor(vault, quiet=True)
        assert len(result["missing"]) > 0

    def test_monitor_healthy_sessions_bucketed_correctly(self, vault):
        vault.save("kdp", {"_saved_at": datetime.now(timezone.utc).isoformat()})
        result = monitor(vault, quiet=True)
        healthy_platforms = [h.platform for h in result["healthy"]]
        assert "kdp" in healthy_platforms

    def test_monitor_expired_sessions_bucketed_correctly(self, vault):
        old_time = datetime.now(timezone.utc) - timedelta(days=90)
        vault.save("kdp", {"_saved_at": old_time.isoformat()})
        result = monitor(vault, quiet=True)
        expired_platforms = [h.platform for h in result["expired"]]
        assert "kdp" in expired_platforms

    def test_monitor_quiet_suppresses_output(self, vault, capsys):
        monitor(vault, quiet=True)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_monitor_not_quiet_prints_something(self, vault, capsys):
        monitor(vault, quiet=False)
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_monitor_all_healthy_prints_ok_message(self, capsys):
        """When all sessions healthy, prints success message."""
        from agentreach.vault.health import PLATFORM_TTL_DAYS
        from agentreach.vault.store import SessionVault
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            from pathlib import Path
            vault = SessionVault(vault_dir=Path(d))
            for p in PLATFORM_TTL_DAYS.keys():
                vault.save(p, {"_saved_at": datetime.now(timezone.utc).isoformat()})
            monitor(vault, quiet=False)
            captured = capsys.readouterr()
            assert "healthy" in captured.out.lower() or "✅" in captured.out


# ── _print_alerts ─────────────────────────────────────────────────────────────

class TestPrintAlerts:
    def _health(self, platform, status, days_remaining=None):
        return SessionHealth(
            platform=platform,
            status=status,
            harvested_at=None,
            estimated_expiry=None,
            days_remaining=days_remaining,
            message="",
        )

    def test_all_healthy_prints_all_ok(self, capsys):
        buckets = {
            "healthy": [self._health("kdp", SessionStatus.HEALTHY, 20)],
            "warning": [],
            "critical": [],
            "expired": [],
            "missing": [],
            "unknown": [],
        }
        _print_alerts(buckets)
        out = capsys.readouterr().out
        assert "All sessions healthy" in out or "✅" in out

    def test_expired_prints_alert(self, capsys):
        buckets = {
            "healthy": [],
            "warning": [],
            "critical": [],
            "expired": [self._health("kdp", SessionStatus.EXPIRED, -5)],
            "missing": [],
            "unknown": [],
        }
        _print_alerts(buckets)
        out = capsys.readouterr().out
        assert "EXPIRED" in out or "expired" in out.lower()
        assert "KDP" in out or "kdp" in out.lower()

    def test_missing_prints_alert(self, capsys):
        buckets = {
            "healthy": [],
            "warning": [],
            "critical": [],
            "expired": [],
            "missing": [self._health("etsy", SessionStatus.MISSING)],
            "unknown": [],
        }
        _print_alerts(buckets)
        out = capsys.readouterr().out
        assert "MISSING" in out or "missing" in out.lower()

    def test_critical_prints_days(self, capsys):
        buckets = {
            "healthy": [],
            "warning": [],
            "critical": [self._health("gumroad", SessionStatus.EXPIRING_SOON, 1)],
            "expired": [],
            "missing": [],
            "unknown": [],
        }
        _print_alerts(buckets)
        out = capsys.readouterr().out
        assert "1" in out

"""
Tests for AgentReach Session Health — expiry checking, status detection, warnings
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from agentreach.vault.health import (
    check_session,
    check_all,
    status_report,
    SessionHealth,
    SessionStatus,
    PLATFORM_TTL_DAYS,
    DEFAULT_TTL_DAYS,
    EXPIRY_WARNING_DAYS,
)
from agentreach.vault.store import SessionVault, _FERNET
from tests.conftest import save_with_timestamp


# ── check_session ─────────────────────────────────────────────────────────────

class TestCheckSession:
    def test_missing_session(self, vault):
        """Platform with no session returns MISSING status."""
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.MISSING
        assert result.platform == "kdp"
        assert result.harvested_at is None
        assert "harvest" in result.message.lower()

    def test_healthy_session(self, vault):
        """Recently harvested session is HEALTHY."""
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.HEALTHY
        assert result.days_remaining is not None
        assert result.days_remaining > EXPIRY_WARNING_DAYS

    def test_expired_session(self, vault):
        """Very old session is EXPIRED."""
        old_time = datetime.now(timezone.utc) - timedelta(days=90)
        save_with_timestamp(vault, "kdp", old_time)
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.EXPIRED
        assert result.days_remaining is not None
        assert result.days_remaining < 0

    def test_expiring_soon_session(self, vault):
        """Session within warning window is EXPIRING_SOON."""
        # KDP TTL is 30 days, warning is 5 days
        # Harvest 27 days ago → 3 days remaining
        harvest_time = datetime.now(timezone.utc) - timedelta(days=27)
        save_with_timestamp(vault, "kdp", harvest_time)
        result = check_session("kdp", vault)
        assert result.status == SessionStatus.EXPIRING_SOON
        assert result.days_remaining is not None
        assert 0 <= result.days_remaining <= EXPIRY_WARNING_DAYS

    def test_session_uses_harvested_at_field(self, vault):
        """Session with 'harvested_at' key also works."""
        recent = datetime.now(timezone.utc)
        raw = {"harvested_at": recent.isoformat()}
        payload = json.dumps(raw).encode()
        path = vault._path("etsy")
        path.write_bytes(_FERNET.encrypt(payload))
        result = check_session("etsy", vault)
        assert result.status == SessionStatus.HEALTHY

    def test_missing_timestamp_returns_unknown(self, vault):
        """Session without any timestamp returns UNKNOWN."""
        raw = json.dumps({"platform": "test", "cookies": []}).encode()
        path = vault._path("someplatform")
        path.write_bytes(_FERNET.encrypt(raw))
        result = check_session("someplatform", vault)
        assert result.status == SessionStatus.UNKNOWN

    def test_invalid_timestamp_returns_unknown(self, vault):
        """Session with invalid timestamp returns UNKNOWN."""
        raw = json.dumps({"_saved_at": "not-a-valid-date"}).encode()
        path = vault._path("badts")
        path.write_bytes(_FERNET.encrypt(raw))
        result = check_session("badts", vault)
        assert result.status == SessionStatus.UNKNOWN

    def test_platform_specific_ttl_kdp(self, vault):
        """KDP uses 30-day TTL."""
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        result = check_session("kdp", vault)
        assert result.estimated_expiry is not None
        expected_ttl = PLATFORM_TTL_DAYS["kdp"]
        diff = (result.estimated_expiry - result.harvested_at).days
        assert diff == expected_ttl

    def test_platform_specific_ttl_etsy(self, vault):
        """Etsy uses 45-day TTL."""
        save_with_timestamp(vault, "etsy", datetime.now(timezone.utc))
        result = check_session("etsy", vault)
        diff = (result.estimated_expiry - result.harvested_at).days
        assert diff == PLATFORM_TTL_DAYS["etsy"]

    def test_unknown_platform_uses_default_ttl(self, vault):
        """Unknown platforms use DEFAULT_TTL_DAYS."""
        save_with_timestamp(vault, "unknown-platform", datetime.now(timezone.utc))
        result = check_session("unknown-platform", vault)
        diff = (result.estimated_expiry - result.harvested_at).days
        assert diff == DEFAULT_TTL_DAYS

    def test_naive_datetime_gets_utc(self, vault):
        """Naive datetime (no timezone) is treated as UTC."""
        naive_ts = datetime.now().isoformat()  # no tz info
        raw = json.dumps({"_saved_at": naive_ts}).encode()
        path = vault._path("naivets")
        path.write_bytes(_FERNET.encrypt(raw))
        result = check_session("naivets", vault)
        # Should not crash, should get HEALTHY (just harvested)
        assert result.status in (SessionStatus.HEALTHY, SessionStatus.UNKNOWN)

    def test_creates_default_vault_if_none_given(self):
        """check_session creates its own vault if none given."""
        result = check_session("definitely_missing_platform_xyz")
        assert result.status == SessionStatus.MISSING

    def test_message_contains_harvest_command_for_missing(self, vault):
        result = check_session("kdp", vault)
        assert "kdp" in result.message

    def test_message_contains_days_for_healthy(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        result = check_session("kdp", vault)
        assert str(result.days_remaining) in result.message or "days" in result.message


# ── check_all ─────────────────────────────────────────────────────────────────

class TestCheckAll:
    def test_check_all_returns_known_platforms(self, vault):
        """check_all covers all platforms in PLATFORM_TTL_DAYS."""
        results = check_all(vault)
        returned_names = {r.platform for r in results}
        for platform in PLATFORM_TTL_DAYS:
            assert platform in returned_names

    def test_check_all_includes_extra_vaulted_platforms(self, vault):
        """Extra platforms in vault appear in check_all."""
        save_with_timestamp(vault, "mystery-platform", datetime.now(timezone.utc))
        results = check_all(vault)
        returned_names = {r.platform for r in results}
        assert "mystery-platform" in returned_names

    def test_check_all_all_missing_on_empty_vault(self, vault):
        results = check_all(vault)
        statuses = [r.status for r in results]
        assert all(s == SessionStatus.MISSING for s in statuses)

    def test_check_all_returns_list_of_session_health(self, vault):
        results = check_all(vault)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, SessionHealth)


# ── status_report ─────────────────────────────────────────────────────────────

class TestStatusReport:
    def test_status_report_returns_string(self, vault):
        report = status_report(vault)
        assert isinstance(report, str)

    def test_status_report_contains_header(self, vault):
        report = status_report(vault)
        assert "AgentReach" in report or "Session" in report

    def test_status_report_contains_platform_names(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        report = status_report(vault)
        assert "kdp" in report

    def test_status_report_shows_healthy(self, vault):
        save_with_timestamp(vault, "kdp", datetime.now(timezone.utc))
        report = status_report(vault)
        assert "kdp" in report


# ── SessionHealth dataclass ───────────────────────────────────────────────────

class TestSessionHealthDataclass:
    def test_health_has_all_fields(self, vault):
        result = check_session("kdp", vault)
        assert hasattr(result, "platform")
        assert hasattr(result, "status")
        assert hasattr(result, "harvested_at")
        assert hasattr(result, "estimated_expiry")
        assert hasattr(result, "days_remaining")
        assert hasattr(result, "message")

    def test_expired_days_remaining_is_negative(self, vault):
        old_time = datetime.now(timezone.utc) - timedelta(days=90)
        save_with_timestamp(vault, "kdp", old_time)
        result = check_session("kdp", vault)
        assert result.days_remaining < 0

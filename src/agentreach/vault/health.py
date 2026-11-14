"""Estimate stored session health from each platform's expected TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from .store import SessionVault, VaultCorruptedError

PLATFORM_TTL_DAYS = {
    "kdp": 30,
    "etsy": 60,
    "gumroad": 90,
    "pinterest": 30,
    "nextdoor": 30,
}
DEFAULT_TTL_DAYS = 30
EXPIRY_WARNING_DAYS = 7


class SessionStatus(str, Enum):
    HEALTHY = "healthy"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class SessionHealth:
    platform: str
    status: SessionStatus
    harvested_at: datetime | None
    estimated_expiry: datetime | None
    days_remaining: int | None
    message: str


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def check_session(platform: str, vault: SessionVault | None = None) -> SessionHealth:
    name = platform.strip().lower()
    session_vault = vault or SessionVault()
    try:
        data = session_vault.load(name)
    except VaultCorruptedError:
        return SessionHealth(name, SessionStatus.UNKNOWN, None, None, None,
                             f"{name} vault entry is unreadable; re-harvest with: agentreach harvest {name}")

    if data is None:
        return SessionHealth(name, SessionStatus.MISSING, None, None, None,
                             f"No {name} session; harvest with: agentreach harvest {name}")

    harvested_at = _parse_timestamp(data.get("harvested_at")) or _parse_timestamp(data.get("_saved_at"))
    if harvested_at is None:
        return SessionHealth(name, SessionStatus.UNKNOWN, None, None, None,
                             f"{name} session has no valid harvest timestamp")

    ttl_days = PLATFORM_TTL_DAYS.get(name, DEFAULT_TTL_DAYS)
    estimated_expiry = harvested_at + timedelta(days=ttl_days)
    days_remaining = (estimated_expiry - datetime.now(timezone.utc)).days
    if days_remaining < 0:
        status = SessionStatus.EXPIRED
        message = f"{name} session expired; re-harvest with: agentreach harvest {name}"
    elif days_remaining <= EXPIRY_WARNING_DAYS:
        status = SessionStatus.EXPIRING_SOON
        message = f"{name} session expires in {days_remaining} days; consider re-harvesting"
    else:
        status = SessionStatus.HEALTHY
        message = f"{name} session healthy; approximately {days_remaining} days remaining"

    return SessionHealth(name, status, harvested_at, estimated_expiry, days_remaining, message)


def check_all(vault: SessionVault | None = None) -> list[SessionHealth]:
    session_vault = vault or SessionVault()
    platforms = set(PLATFORM_TTL_DAYS) | set(session_vault.list_platforms())
    return [check_session(platform, session_vault) for platform in sorted(platforms)]


def status_report(vault: SessionVault | None = None) -> str:
    results = check_all(vault)
    lines = ["AgentReach Session Status", "=" * 26]
    for health in results:
        days = f" ({health.days_remaining} days remaining)" if health.days_remaining is not None else ""
        lines.append(f"{health.platform}: {health.status.value}{days} - {health.message}")
    return "\n".join(lines)

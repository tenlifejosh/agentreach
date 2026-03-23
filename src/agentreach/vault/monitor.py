"""AgentReach — Session Expiry Monitor.

Categorises sessions as healthy/warning/critical/expired and emits structured alerts.
"""

import logging
from typing import Optional

from .health import SessionHealth, SessionStatus, check_all
from .store import SessionVault

logger = logging.getLogger(__name__)

# Expiry threshold constants (days)
CRITICAL_THRESHOLD_DAYS: int = 2
WARNING_THRESHOLD_DAYS: int = 5


def _categorize(h: SessionHealth) -> str:
    """Map a SessionHealth object to a severity category string.

    Args:
        h: The SessionHealth to categorise.

    Returns:
        One of: ``"healthy"``, ``"warning"``, ``"critical"``, ``"expired"``,
        ``"missing"``, or ``"unknown"``.
    """
    if h.status == SessionStatus.HEALTHY:
        if h.days_remaining is not None and h.days_remaining <= WARNING_THRESHOLD_DAYS:
            return "warning"
        return "healthy"
    if h.status == SessionStatus.EXPIRING_SOON:
        if h.days_remaining is not None and h.days_remaining <= CRITICAL_THRESHOLD_DAYS:
            return "critical"
        return "warning"
    if h.status == SessionStatus.EXPIRED:
        return "expired"
    if h.status == SessionStatus.MISSING:
        return "missing"
    return "unknown"


def monitor(
    vault: Optional[SessionVault] = None,
    quiet: bool = False,
) -> dict[str, list[SessionHealth]]:
    """Check all sessions and categorise them by severity.

    Logs warning/critical/expired alerts to the module logger unless
    ``quiet=True``. Always returns the full categorised result dict.

    Args:
        vault: SessionVault to inspect. A new default vault is created if omitted.
        quiet: When True, suppresses all log output.

    Returns:
        A dict mapping severity category to a list of SessionHealth objects.
        Keys: ``"healthy"``, ``"warning"``, ``"critical"``, ``"expired"``,
        ``"missing"``, ``"unknown"``.
    """
    results = check_all(vault)

    buckets: dict[str, list[SessionHealth]] = {
        "healthy": [],
        "warning": [],
        "critical": [],
        "expired": [],
        "missing": [],
        "unknown": [],
    }

    for h in results:
        cat = _categorize(h)
        buckets[cat].append(h)

    if not quiet:
        _print_alerts(buckets)

    return buckets


def _print_alerts(buckets: dict[str, list[SessionHealth]]) -> None:
    """Print alerts for sessions that require attention (stdout-friendly wrapper).

    This is an alias for :func:`_log_alerts` retained for backward compatibility
    with tests and any external callers that imported this private symbol before
    the logging refactor.

    Args:
        buckets: Categorised SessionHealth dict returned by ``monitor()``.
    """
    needs_attention = (
        buckets["critical"] + buckets["expired"] + buckets["warning"] + buckets["missing"]
    )

    if not needs_attention:
        print("AgentReach: ✅ All sessions healthy — no action required.")
        return

    for h in buckets["expired"]:
        print(f"AgentReach: ❌ {h.platform.upper()} session EXPIRED. Re-harvest: agentreach harvest {h.platform}")

    for h in buckets["critical"]:
        days = h.days_remaining if h.days_remaining is not None else "?"
        print(f"AgentReach: 🔴 {h.platform.upper()} session CRITICAL — expires in {days} day(s).")

    for h in buckets["warning"]:
        days = h.days_remaining if h.days_remaining is not None else "?"
        print(f"AgentReach: ⚠️  {h.platform.upper()} expires in {days} day(s).")

    for h in buckets["missing"]:
        print(f"AgentReach: ○ {h.platform.upper()} is MISSING. Bootstrap: agentreach harvest {h.platform}")

    healthy_count = len(buckets["healthy"])
    if healthy_count:
        healthy_names = ", ".join(h.platform for h in buckets["healthy"])
        print(f"AgentReach: ✅ {healthy_count} platform(s) healthy: {healthy_names}")


def _log_alerts(buckets: dict[str, list[SessionHealth]]) -> None:
    """Emit log messages for sessions that require attention.

    Args:
        buckets: Categorised SessionHealth dict returned by ``monitor()``.
    """
    needs_attention = (
        buckets["critical"] + buckets["expired"] + buckets["warning"] + buckets["missing"]
    )

    if not needs_attention:
        logger.info("AgentReach: all sessions healthy — no action required.")
        return

    for h in buckets["expired"]:
        logger.error(
            "AgentReach: %s session EXPIRED. Re-harvest immediately: agentreach harvest %s",
            h.platform.upper(),
            h.platform,
        )

    for h in buckets["critical"]:
        days = h.days_remaining if h.days_remaining is not None else "?"
        logger.error(
            "AgentReach: %s session CRITICAL — expires in %s day(s). "
            "Re-harvest soon: agentreach harvest %s",
            h.platform.upper(),
            days,
            h.platform,
        )

    for h in buckets["warning"]:
        days = h.days_remaining if h.days_remaining is not None else "?"
        logger.warning(
            "AgentReach: %s session expires in %s day(s). "
            "Schedule re-harvest: agentreach harvest %s",
            h.platform.upper(),
            days,
            h.platform,
        )

    for h in buckets["missing"]:
        logger.warning(
            "AgentReach: %s has no session. Bootstrap with: agentreach harvest %s",
            h.platform.upper(),
            h.platform,
        )

    healthy_count = len(buckets["healthy"])
    if healthy_count:
        healthy_names = ", ".join(h.platform for h in buckets["healthy"])
        logger.info(
            "AgentReach: %d platform(s) healthy: %s",
            healthy_count,
            healthy_names,
        )

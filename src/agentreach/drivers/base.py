"""AgentReach — Base Platform Driver. All platform drivers extend this class."""

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..vault.health import SessionStatus, check_session
from ..vault.store import SessionVault

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a platform upload or action operation.

    Attributes:
        success:    Whether the operation completed successfully.
        platform:   Platform name (e.g. 'kdp', 'etsy').
        product_id: Platform-assigned product or listing ID, if available.
        url:        Public URL to the created/modified resource, if available.
        message:    Human-readable success or status description.
        error:      Human-readable error description when success is False.
    """

    success: bool
    platform: str
    product_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class BasePlatformDriver(ABC):
    """Base class for all AgentReach platform drivers.

    Subclass this and implement:
        - ``platform_name``: str class attribute identifying the platform.
        - ``verify_session()``: async method that checks whether the saved
          session is still authenticated.
        - Any platform-specific action methods (e.g. ``create_pin``, ``post``).

    Example::

        class MyDriver(BasePlatformDriver):
            platform_name = "myplatform"

            async def verify_session(self) -> bool:
                async with platform_context("myplatform", self.vault) as (ctx, page):
                    await page.goto("https://myplatform.com/dashboard")
                    return "login" not in page.url
    """

    platform_name: str = "unknown"

    def __init__(self, vault: Optional[SessionVault] = None) -> None:
        """Initialise the driver with an optional pre-existing vault instance.

        Args:
            vault: SessionVault to use. A new default vault is created if omitted.
        """
        self.vault = vault or SessionVault()

    def check_health(self) -> bool:
        """Return True if the platform session is healthy or expiring-soon.

        Returns:
            True if the session is usable (HEALTHY or EXPIRING_SOON), False otherwise.
        """
        health = check_session(self.platform_name, self.vault)
        return health.status in (SessionStatus.HEALTHY, SessionStatus.EXPIRING_SOON)

    def require_valid_session(self) -> None:
        """Assert that a usable session exists before running any operation.

        Logs a clear message and exits with code 1 if the session is expired
        or missing. Logs a warning (but does not exit) if the session is
        expiring soon.

        Raises:
            SystemExit: With exit code 1 when the session is expired or missing.
        """
        health = check_session(self.platform_name, self.vault)

        if health.status == SessionStatus.EXPIRED:
            logger.error(
                "%s session is expired. Re-harvest with: agentreach harvest %s",
                self.platform_name.upper(),
                self.platform_name,
            )
            sys.exit(1)

        elif health.status == SessionStatus.MISSING:
            logger.error(
                "No %s session found. Bootstrap with: agentreach harvest %s",
                self.platform_name.upper(),
                self.platform_name,
            )
            sys.exit(1)

        elif health.status == SessionStatus.EXPIRING_SOON:
            days = health.days_remaining if health.days_remaining is not None else "?"
            logger.warning(
                "%s session expires in %s day(s). Re-harvest soon: agentreach harvest %s",
                self.platform_name.upper(),
                days,
                self.platform_name,
            )

        elif health.status == SessionStatus.UNKNOWN:
            logger.warning(
                "%s session state is unknown. If errors occur, re-harvest: agentreach harvest %s",
                self.platform_name.upper(),
                self.platform_name,
            )

    @abstractmethod
    async def verify_session(self) -> bool:
        """Verify the saved session is still authenticated.

        Loads the session from the vault, opens a headless browser, navigates
        to a logged-in-only page, and confirms the session is active.

        Returns:
            True if the session is authenticated and usable. False otherwise.
        """

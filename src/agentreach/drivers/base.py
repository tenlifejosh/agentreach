"""AgentReach — Base Platform Driver. All platform drivers extend this class."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Optional, TypeVar

from ..vault.health import SessionStatus, check_session
from ..vault.store import SessionVault

_T = TypeVar("_T")


def run_async(coro: Awaitable[_T]) -> _T:
    """Run an async coroutine safely regardless of whether an event loop is running.

    ``asyncio.run()`` raises RuntimeError when called from within an already-running
    event loop (e.g. when called from an AI agent framework, Jupyter, or any async
    host process). This helper detects that situation and uses the existing loop
    via ``loop.run_until_complete()`` instead.

    Args:
        coro: An awaitable (coroutine) to run.

    Returns:
        The return value of the coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop is running — safe to use asyncio.run()
        return asyncio.run(coro)  # type: ignore[return-value]

    # An event loop IS running (e.g. inside an AI agent or Jupyter).
    # Submit as a task and wait for it. This requires the caller's loop to be
    # able to process events (i.e. not be blocked). For truly synchronous callers
    # inside a running loop, prefer awaiting the async method directly.
    import concurrent.futures
    import threading

    result_container: list[Any] = []
    exception_container: list[BaseException] = []

    def run_in_thread() -> None:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result_container.append(new_loop.run_until_complete(coro))
        except BaseException as exc:  # noqa: BLE001
            exception_container.append(exc)
        finally:
            new_loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    thread.join()

    if exception_container:
        raise exception_container[0]
    return result_container[0]  # type: ignore[return-value]

logger = logging.getLogger(__name__)


class SessionExpiredError(RuntimeError):
    """Raised when the platform session is expired and must be re-harvested."""


class InvalidSessionError(RuntimeError):
    """Raised when no session exists for the platform."""


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

        Logs a clear message and raises an exception if the session is expired
        or missing. Logs a warning (but does not raise) if the session is
        expiring soon.

        Raises:
            SessionExpiredError: When the session is expired.
            InvalidSessionError: When no session exists for this platform.
        """
        health = check_session(self.platform_name, self.vault)

        if health.status == SessionStatus.EXPIRED:
            msg = (
                f"{self.platform_name.upper()} session is expired. "
                f"Re-harvest with: agentreach harvest {self.platform_name}"
            )
            logger.error(msg)
            raise SessionExpiredError(msg)

        elif health.status == SessionStatus.MISSING:
            msg = (
                f"No {self.platform_name.upper()} session found. "
                f"Bootstrap with: agentreach harvest {self.platform_name}"
            )
            logger.error(msg)
            raise InvalidSessionError(msg)

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

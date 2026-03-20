"""
AgentReach — Base Platform Driver
All platform drivers extend this class.
"""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from ..vault.store import SessionVault
from ..vault.health import check_session, SessionStatus


@dataclass
class UploadResult:
    success: bool
    platform: str
    product_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class BasePlatformDriver(ABC):
    """
    Base class for all AgentReach platform drivers.

    Subclass this and implement:
        - platform_name: str
        - verify_session(): async check login is still valid
        - Any platform-specific action methods
    """

    platform_name: str = "unknown"

    def __init__(self, vault: Optional[SessionVault] = None):
        self.vault = vault or SessionVault()

    def check_health(self) -> bool:
        health = check_session(self.platform_name, self.vault)
        return health.status in (SessionStatus.HEALTHY, SessionStatus.EXPIRING_SOON)

    def require_valid_session(self) -> None:
        """
        Check session health before any operation.
        If expired or missing: print a friendly message and exit cleanly.
        No stack traces.
        """
        health = check_session(self.platform_name, self.vault)

        if health.status == SessionStatus.EXPIRED:
            print(
                f"\n❌  {self.platform_name.upper()} session expired.\n"
                f"    Re-harvest with:\n"
                f"    agentreach harvest {self.platform_name}\n"
            )
            sys.exit(1)

        elif health.status == SessionStatus.MISSING:
            print(
                f"\n○   No {self.platform_name.upper()} session found.\n"
                f"    Bootstrap with:\n"
                f"    agentreach harvest {self.platform_name}\n"
            )
            sys.exit(1)

        elif health.status == SessionStatus.EXPIRING_SOON:
            days = health.days_remaining if health.days_remaining is not None else "?"
            print(
                f"⚠️   {self.platform_name.upper()} session expires in {days} days.\n"
                f"    Consider re-harvesting soon: agentreach harvest {self.platform_name}"
            )
            # Don't exit — session still works, just warn

        elif health.status == SessionStatus.UNKNOWN:
            print(
                f"?   {self.platform_name.upper()} session state unknown.\n"
                f"    If issues arise, re-harvest: agentreach harvest {self.platform_name}"
            )

    @abstractmethod
    async def verify_session(self) -> bool:
        """
        Verify the saved session is still valid by loading it and
        checking a logged-in-only page. Returns True if authenticated.
        """
        pass

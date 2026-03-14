"""
AgentReach — Base Platform Driver
All platform drivers extend this class.
"""

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
        return health.status == SessionStatus.HEALTHY or health.status == SessionStatus.EXPIRING_SOON

    @abstractmethod
    async def verify_session(self) -> bool:
        """
        Verify the saved session is still valid by loading it and
        checking a logged-in-only page. Returns True if authenticated.
        """
        pass

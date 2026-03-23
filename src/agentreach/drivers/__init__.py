"""AgentReach platform drivers — registry and factory."""

from .base import BasePlatformDriver, UploadResult
from .etsy import EtsyDriver
from .gumroad import GumroadDriver
from .kdp import KDPDriver
from .nextdoor import NextdoorDriver
from .pinterest import PinterestDriver
from .reddit import RedditDriver
from .twitter import TwitterDriver

# Registry mapping platform name → driver class
DRIVERS: dict[str, type[BasePlatformDriver]] = {
    "etsy":      EtsyDriver,
    "gumroad":   GumroadDriver,
    "kdp":       KDPDriver,
    "nextdoor":  NextdoorDriver,
    "pinterest": PinterestDriver,
    "reddit":    RedditDriver,
    "twitter":   TwitterDriver,
}


def get_driver(platform: str) -> BasePlatformDriver:
    """Instantiate and return the driver for the given platform name.

    Args:
        platform: Case-insensitive platform identifier (e.g. 'kdp', 'etsy').

    Returns:
        A new instance of the appropriate :class:`BasePlatformDriver` subclass.

    Raises:
        ValueError: If the platform name is not registered in ``DRIVERS``.
    """
    platform = platform.lower()
    driver_cls = DRIVERS.get(platform)
    if not driver_cls:
        raise ValueError(
            f"Unknown platform: '{platform}'. "
            f"Available platforms: {sorted(DRIVERS.keys())}"
        )
    return driver_cls()

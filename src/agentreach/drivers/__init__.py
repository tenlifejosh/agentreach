from .kdp import KDPDriver
from .etsy import EtsyDriver
from .gumroad import GumroadDriver
from .pinterest import PinterestDriver
from .reddit import RedditDriver
from .twitter import TwitterDriver
from .base import BasePlatformDriver, UploadResult


DRIVERS = {
    "kdp": KDPDriver,
    "etsy": EtsyDriver,
    "gumroad": GumroadDriver,
    "pinterest": PinterestDriver,
    "reddit": RedditDriver,
    "twitter": TwitterDriver,
}


def get_driver(platform: str) -> BasePlatformDriver:
    platform = platform.lower()
    driver_cls = DRIVERS.get(platform)
    if not driver_cls:
        raise ValueError(f"Unknown platform: '{platform}'. Available: {list(DRIVERS.keys())}")
    return driver_cls()

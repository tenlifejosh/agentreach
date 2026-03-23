# AgentReach — Community Driver Marketplace & Plugin Architecture
**Version:** 1.0  
**Date:** 2026-03-23  
**Author:** Hutch (Navigator subagent)  
**Status:** Design Draft — Ready for Implementation

---

## Vision

AgentReach becomes the universal agent portal — the single authenticated layer between any AI agent and any web platform. Today it has 7 drivers. The ceiling is unlimited: any AI agent, any framework, any platform — connected through one system with community-built drivers.

The goal: **`agentreach install shopify` and you're done.** Community members build drivers. Users install them. Agents use them.

---

## Table of Contents

1. [Plugin Architecture](#1-plugin-architecture)
2. [Driver SDK & Template](#2-driver-sdk--template)
3. [Registry Design](#3-registry-design)
4. [Priority Drivers to Build](#4-priority-drivers-to-build)
5. [Skill Packs](#5-skill-packs)
6. [LangChain / CrewAI / AutoGen Integration](#6-langchain--crewai--autogen-integration)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Plugin Architecture

### 1.1 Design Principles

- **Zero core changes to install a driver** — third-party drivers never touch core AgentReach files
- **Isolation** — community drivers run in the same process but are loaded via a clean registry layer
- **Discovery** — `agentreach search shopify` finds it; `agentreach install shopify` installs it
- **Versioning** — drivers are versioned packages; pinning and upgrades work like pip

### 1.2 How It Works

Third-party drivers are installed as standard Python packages with a specific naming convention and entry-point declaration. AgentReach discovers them at runtime via Python's `importlib.metadata` entry points — no config files to maintain, no manual registration.

**Package naming convention:** `agentreach-driver-<platform>`

Examples:
- `agentreach-driver-shopify`
- `agentreach-driver-wordpress`
- `agentreach-driver-linkedin`

**Entry point declaration** (in the driver's `pyproject.toml`):
```toml
[project.entry-points."agentreach.drivers"]
shopify = "agentreach_driver_shopify:ShopifyDriver"
```

AgentReach scans for all registered `agentreach.drivers` entry points at startup and merges them with the built-in DRIVERS registry.

### 1.3 Plugin Loader

```python
# src/agentreach/plugins.py

from importlib.metadata import entry_points
from typing import Type, Dict
import logging

logger = logging.getLogger(__name__)


def discover_drivers() -> Dict[str, Type]:
    """
    Scan installed packages for agentreach.drivers entry points.
    Returns a dict of {platform_name: DriverClass}.
    
    Community drivers declare themselves via pyproject.toml:
        [project.entry-points."agentreach.drivers"]
        shopify = "agentreach_driver_shopify:ShopifyDriver"
    """
    discovered = {}
    
    try:
        eps = entry_points(group="agentreach.drivers")
    except Exception:
        return discovered
    
    for ep in eps:
        try:
            driver_cls = ep.load()
            platform = ep.name.lower()
            discovered[platform] = driver_cls
            logger.debug(f"Loaded community driver: {platform} from {ep.value}")
        except Exception as e:
            logger.warning(f"Failed to load driver '{ep.name}': {e}")
    
    return discovered


def get_all_drivers() -> Dict[str, Type]:
    """Merge built-in drivers with community-installed drivers."""
    from .drivers import DRIVERS  # built-in drivers
    
    community = discover_drivers()
    
    # Community drivers can override built-in drivers (allows hot-fixes)
    merged = {**DRIVERS, **community}
    return merged


def get_driver(platform: str):
    """Get a driver instance by platform name. Checks community drivers first."""
    all_drivers = get_all_drivers()
    platform = platform.lower()
    
    driver_cls = all_drivers.get(platform)
    if not driver_cls:
        available = sorted(all_drivers.keys())
        raise ValueError(
            f"Unknown platform: '{platform}'.\n"
            f"Built-in: {[k for k in available if k in BUILT_IN_PLATFORMS]}\n"
            f"Installed: {[k for k in available if k not in BUILT_IN_PLATFORMS]}\n"
            f"Install more: agentreach search {platform}"
        )
    
    return driver_cls()
```

### 1.4 CLI Install/Search Commands

```python
# Added to cli.py

@app.command()
def install(
    driver: str = typer.Argument(..., help="Driver name or package (e.g. 'shopify' or 'agentreach-driver-shopify')"),
    version: Optional[str] = typer.Option(None, help="Pin a specific version (e.g. 1.2.0)"),
):
    """
    Install a community driver.
    
    Examples:
        agentreach install shopify
        agentreach install wordpress --version 1.0.0
        agentreach install https://github.com/you/agentreach-driver-custom
    """
    import subprocess, sys
    
    # Normalize: 'shopify' → 'agentreach-driver-shopify'
    if not driver.startswith("agentreach-driver-") and not driver.startswith("http"):
        package = f"agentreach-driver-{driver}"
    else:
        package = driver
    
    if version:
        package = f"{package}=={version}"
    
    console.print(f"[bold]📦 Installing {package}...[/bold]")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        rprint(f"[green]✅ Installed {package}[/green]")
        rprint(f"   Run [cyan]agentreach harvest {driver}[/cyan] to set up your session.")
    else:
        rprint(f"[red]❌ Install failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)


@app.command()
def uninstall(
    driver: str = typer.Argument(..., help="Driver to remove (e.g. 'shopify')"),
):
    """Uninstall a community driver."""
    import subprocess, sys
    
    if not driver.startswith("agentreach-driver-"):
        package = f"agentreach-driver-{driver}"
    else:
        package = driver
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", package],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        rprint(f"[green]✅ Removed {package}[/green]")
    else:
        rprint(f"[red]❌ Uninstall failed: {result.stderr}[/red]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Platform or keyword to search for"),
):
    """Search the AgentReach driver registry for available drivers."""
    import httpx
    
    try:
        # Query PyPI for agentreach-driver-* packages matching the query
        resp = httpx.get(
            f"https://pypi.org/pypi/agentreach-driver-{query}/json",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            info = data["info"]
            rprint(f"[bold cyan]Found:[/bold cyan] {info['name']} v{info['version']}")
            rprint(f"  {info['summary']}")
            rprint(f"  Install: [yellow]agentreach install {query}[/yellow]")
        else:
            # Fall back to PyPI simple search
            rprint(f"[yellow]No driver found for '{query}' on PyPI.[/yellow]")
            rprint(f"  Check GitHub: https://github.com/topics/agentreach-driver")
            rprint(f"  Or build one: agentreach scaffold {query}")
    except Exception as e:
        rprint(f"[red]Search failed: {e}[/red]")


@app.command()
def scaffold(
    platform: str = typer.Argument(..., help="Platform name for the new driver (e.g. 'shopify')"),
    output_dir: Optional[Path] = typer.Option(None, help="Where to create the scaffold"),
):
    """
    Generate a new driver scaffold from template.
    Creates a ready-to-develop driver package for any platform.
    """
    from .plugins import scaffold_driver
    out = output_dir or Path.cwd() / f"agentreach-driver-{platform}"
    scaffold_driver(platform, out)
    rprint(f"[green]✅ Scaffold created:[/green] {out}")
    rprint(f"   Next: cd {out} && pip install -e . && agentreach harvest {platform}")


@app.command("list-drivers")
def list_drivers():
    """List all installed drivers (built-in + community)."""
    from .plugins import get_all_drivers
    from .drivers import DRIVERS as BUILTIN_DRIVERS
    
    all_drivers = get_all_drivers()
    
    table = Table(title="🦾 AgentReach — Installed Drivers", show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="bold", min_width=16)
    table.add_column("Type", min_width=12)
    table.add_column("Class", min_width=30)
    table.add_column("Version", min_width=10)
    
    for name, cls in sorted(all_drivers.items()):
        driver_type = "built-in" if name in BUILTIN_DRIVERS else "[cyan]community[/cyan]"
        version = getattr(cls, "version", "—")
        table.add_row(name, driver_type, f"{cls.__module__}.{cls.__name__}", version)
    
    console.print(table)
```

### 1.5 Scaffold Generator

```python
# src/agentreach/plugins.py (continued)

SCAFFOLD_TEMPLATE = '''"""
AgentReach Driver — {platform_title}
Community driver for {platform_title} platform.

Install: pip install agentreach-driver-{platform}
Setup:   agentreach harvest {platform}
"""

from agentreach.drivers.base import BasePlatformDriver, UploadResult
from agentreach.vault.store import SessionVault
from typing import Optional


class {class_name}Driver(BasePlatformDriver):
    """
    AgentReach driver for {platform_title}.
    
    Authentication: {auth_method}
    """
    
    platform_name = "{platform}"
    version = "0.1.0"
    
    # ── Metadata (shown in registry) ─────────────────────────────────────────
    description = "AgentReach driver for {platform_title}"
    author = ""
    homepage = ""
    tags = ["{platform}"]
    
    def __init__(self, vault: Optional[SessionVault] = None):
        super().__init__(vault)
    
    async def verify_session(self) -> bool:
        """
        Verify the saved session is still valid.
        Should load the session and make a lightweight authenticated request.
        Return True if authenticated, False otherwise.
        """
        raise NotImplementedError
    
    # ── Add your platform-specific methods below ──────────────────────────────
    # Examples:
    #   async def create_listing(self, ...) -> UploadResult
    #   async def post_content(self, ...) -> UploadResult
    #   async def get_analytics(self, ...) -> dict
'''

PYPROJECT_TEMPLATE = '''[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agentreach-driver-{platform}"
version = "0.1.0"
description = "AgentReach driver for {platform_title}"
requires-python = ">=3.10"
dependencies = [
    "agentreach>=0.2.0",
]

[project.entry-points."agentreach.drivers"]
{platform} = "agentreach_driver_{platform_underscore}:{class_name}Driver"

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/agentreach-driver-{platform}"
'''

def scaffold_driver(platform: str, output_dir: Path) -> None:
    """Generate a driver scaffold from templates."""
    platform_clean = platform.lower().replace("-", "_").replace(" ", "_")
    platform_title = platform.replace("-", " ").replace("_", " ").title()
    class_name = platform_title.replace(" ", "")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    src_dir = output_dir / f"agentreach_driver_{platform_clean}"
    src_dir.mkdir(exist_ok=True)
    
    # Write driver module
    (src_dir / "__init__.py").write_text(
        f"from .driver import {class_name}Driver\n__all__ = ['{class_name}Driver']\n"
    )
    (src_dir / "driver.py").write_text(
        SCAFFOLD_TEMPLATE.format(
            platform=platform_clean,
            platform_title=platform_title,
            class_name=class_name,
            platform_underscore=platform_clean,
            auth_method="Browser cookie harvest (default) or API token",
        )
    )
    
    # Write pyproject.toml
    (output_dir / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(
            platform=platform_clean,
            platform_title=platform_title,
            class_name=class_name,
            platform_underscore=platform_clean,
        )
    )
    
    # Write README stub
    (output_dir / "README.md").write_text(
        f"# agentreach-driver-{platform_clean}\n\n"
        f"AgentReach community driver for **{platform_title}**.\n\n"
        f"## Install\n\n```bash\nagentreach install {platform_clean}\n```\n\n"
        f"## Setup\n\n```bash\nagentreach harvest {platform_clean}\n```\n\n"
        f"## Usage\n\n```python\nfrom agentreach.plugins import get_driver\n\n"
        f"driver = get_driver('{platform_clean}')\n# driver.your_method(...)\n```\n"
    )
    
    # Write test stub
    tests_dir = output_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / f"test_{platform_clean}_driver.py").write_text(
        f"\"\"\"Tests for {platform_title} driver.\"\"\"\n\n"
        f"import pytest\n"
        f"from agentreach_driver_{platform_clean} import {class_name}Driver\n\n\n"
        f"def test_driver_has_platform_name():\n"
        f"    assert {class_name}Driver.platform_name == '{platform_clean}'\n\n\n"
        f"def test_driver_inherits_base():\n"
        f"    from agentreach.drivers.base import BasePlatformDriver\n"
        f"    assert issubclass({class_name}Driver, BasePlatformDriver)\n\n\n"
        f"@pytest.mark.asyncio\n"
        f"async def test_verify_session_not_implemented():\n"
        f"    \"\"\"Override this test when verify_session is implemented.\"\"\"\n"
        f"    driver = {class_name}Driver()\n"
        f"    with pytest.raises(NotImplementedError):\n"
        f"        await driver.verify_session()\n"
    )
```

---

## 2. Driver SDK & Template

### 2.1 Enhanced Base Class

The current `BasePlatformDriver` is minimal. The SDK version adds lifecycle hooks, metadata, capability declarations, and a richer result model.

```python
# src/agentreach/drivers/base.py (enhanced)

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict, List
from pathlib import Path

from ..vault.store import SessionVault
from ..vault.health import check_session, SessionStatus


class AuthMethod(str, Enum):
    BROWSER_COOKIE = "browser_cookie"   # Cookie harvest via visible browser
    API_TOKEN      = "api_token"        # Static API key/token
    OAUTH2         = "oauth2"           # OAuth2 flow
    BASIC_AUTH     = "basic_auth"       # Username + password
    COMBINED       = "combined"         # Multiple methods


class DriverCapability(str, Enum):
    """Declare what your driver can do. Used by skill packs and agent orchestrators."""
    POST_CONTENT     = "post_content"      # Post text/images
    UPLOAD_PRODUCT   = "upload_product"    # Create/upload a product listing
    READ_ANALYTICS   = "read_analytics"    # Pull analytics data
    MANAGE_INVENTORY = "manage_inventory"  # Update stock, prices
    SEND_MESSAGE     = "send_message"      # DM / messaging
    SCRAPE_DATA      = "scrape_data"       # Extract structured data
    SEARCH           = "search"            # Search the platform
    COMMENT          = "comment"           # Comment on content
    FOLLOW           = "follow"            # Follow users/pages


@dataclass
class DriverResult:
    """Unified result type for all driver operations."""
    success: bool
    platform: str
    operation: str = ""          # e.g. "create_listing", "post_content"
    resource_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)  # operation-specific output
    
    # Legacy alias
    @property
    def product_id(self) -> Optional[str]:
        return self.resource_id


# Keep UploadResult as alias for backward compatibility
UploadResult = DriverResult


class BasePlatformDriver(ABC):
    """
    Base class for all AgentReach platform drivers.
    
    Required:
        platform_name: str          — machine-readable platform id (lowercase, no spaces)
        verify_session() -> bool    — check if current session is valid
    
    Recommended:
        version: str                — driver version (semver)
        description: str            — one-line description
        auth_method: AuthMethod     — how this driver authenticates
        capabilities: List[...]     — what this driver can do
    
    Lifecycle hooks (optional override):
        on_install()                — called once after first install
        on_session_loaded()         — called every time a session is loaded
        on_session_expired()        — called when session expires
    """
    
    # ── Required class attributes ─────────────────────────────────────────────
    platform_name: str = "unknown"
    
    # ── Recommended metadata ──────────────────────────────────────────────────
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    auth_method: AuthMethod = AuthMethod.BROWSER_COOKIE
    capabilities: List[DriverCapability] = []
    tags: List[str] = []
    
    def __init__(self, vault: Optional[SessionVault] = None):
        self.vault = vault or SessionVault()
        self._session_data: Optional[Dict] = None
    
    # ── Session management ────────────────────────────────────────────────────
    
    def check_health(self) -> bool:
        health = check_session(self.platform_name, self.vault)
        return health.status in (SessionStatus.HEALTHY, SessionStatus.EXPIRING_SOON)
    
    def require_valid_session(self) -> None:
        """Check session health. Exits cleanly with guidance if invalid."""
        import sys
        health = check_session(self.platform_name, self.vault)
        
        if health.status == SessionStatus.EXPIRED:
            print(
                f"\n❌  {self.platform_name.upper()} session expired.\n"
                f"    Re-harvest: agentreach harvest {self.platform_name}\n"
            )
            sys.exit(1)
        elif health.status == SessionStatus.MISSING:
            print(
                f"\n○   No {self.platform_name.upper()} session found.\n"
                f"    Bootstrap: agentreach harvest {self.platform_name}\n"
            )
            sys.exit(1)
        elif health.status == SessionStatus.EXPIRING_SOON:
            days = health.days_remaining or "?"
            print(
                f"⚠️   {self.platform_name.upper()} session expires in {days} days.\n"
                f"    Consider: agentreach harvest {self.platform_name}"
            )
    
    def load_session_data(self) -> Optional[Dict]:
        """Load raw session data from vault. Cache in self._session_data."""
        if self._session_data is None:
            self._session_data = self.vault.load(self.platform_name)
        return self._session_data
    
    def save_session_data(self, data: Dict) -> None:
        """Save/update session data in vault."""
        self._session_data = data
        self.vault.save(self.platform_name, data)
    
    # ── Lifecycle hooks ───────────────────────────────────────────────────────
    
    def on_install(self) -> None:
        """Called once after first installation. Override for setup logic."""
        pass
    
    def on_session_loaded(self) -> None:
        """Called every time a valid session is loaded. Override for setup."""
        pass
    
    def on_session_expired(self) -> None:
        """Called when session expiry is detected. Override for cleanup."""
        pass
    
    # ── Abstract methods ──────────────────────────────────────────────────────
    
    @abstractmethod
    async def verify_session(self) -> bool:
        """
        Verify the saved session is still valid by making a live request.
        Should be lightweight — a single authenticated API call or page check.
        Returns True if authenticated, False if session is dead.
        """
        pass
    
    # ── Utility helpers ───────────────────────────────────────────────────────
    
    def _success(self, operation: str, resource_id: str = None, 
                 url: str = None, message: str = "", **data) -> DriverResult:
        return DriverResult(
            success=True, platform=self.platform_name,
            operation=operation, resource_id=resource_id,
            url=url, message=message, data=data
        )
    
    def _error(self, operation: str, error: str) -> DriverResult:
        return DriverResult(
            success=False, platform=self.platform_name,
            operation=operation, error=error
        )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.platform_name} v{self.version}>"
```

### 2.2 Complete Driver Example (Shopify)

This example demonstrates every pattern: API auth, multiple capabilities, lifecycle hooks, sync wrappers.

```python
# agentreach_driver_shopify/driver.py

"""
AgentReach Driver — Shopify
Manages products, orders, and inventory via Shopify Admin API.

Install: agentreach install shopify
Setup:   agentreach shopify set-credentials --shop mystore.myshopify.com --token shpat_xxx
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, List
import httpx

from agentreach.drivers.base import (
    BasePlatformDriver, DriverResult, AuthMethod, DriverCapability
)
from agentreach.vault.store import SessionVault


@dataclass
class ShopifyProduct:
    title: str
    description: str          # HTML allowed
    price: float
    vendor: str = ""
    product_type: str = ""
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)     # local paths or URLs
    sku: str = ""
    inventory_qty: int = 0
    published: bool = True


class ShopifyDriver(BasePlatformDriver):
    platform_name = "shopify"
    version = "1.0.0"
    description = "Shopify store management via Admin API"
    auth_method = AuthMethod.API_TOKEN
    capabilities = [
        DriverCapability.UPLOAD_PRODUCT,
        DriverCapability.MANAGE_INVENTORY,
        DriverCapability.READ_ANALYTICS,
    ]
    tags = ["ecommerce", "shopify", "products", "inventory"]
    
    API_VERSION = "2024-01"
    
    def __init__(
        self,
        shop_domain: Optional[str] = None,
        access_token: Optional[str] = None,
        vault: Optional[SessionVault] = None,
    ):
        super().__init__(vault)
        self._shop_domain = shop_domain
        self._access_token = access_token
    
    # ── Credentials ───────────────────────────────────────────────────────────
    
    def _get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Returns (shop_domain, access_token)."""
        if self._shop_domain and self._access_token:
            return self._shop_domain, self._access_token
        
        import os
        domain = self._shop_domain or os.environ.get("SHOPIFY_SHOP_DOMAIN")
        token = self._access_token or os.environ.get("SHOPIFY_ACCESS_TOKEN")
        
        if not (domain and token):
            data = self.load_session_data()
            if data:
                domain = domain or data.get("shop_domain")
                token = token or data.get("access_token")
        
        return domain, token
    
    def save_credentials(self, shop_domain: str, access_token: str) -> None:
        self.save_session_data({
            "shop_domain": shop_domain,
            "access_token": access_token,
        })
        print(f"✅ Shopify credentials saved.")
    
    def _api_url(self, path: str) -> str:
        domain, _ = self._get_credentials()
        return f"https://{domain}/admin/api/{self.API_VERSION}/{path}"
    
    def _headers(self) -> dict:
        _, token = self._get_credentials()
        return {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        }
    
    # ── Session verification ──────────────────────────────────────────────────
    
    async def verify_session(self) -> bool:
        domain, token = self._get_credentials()
        if not (domain and token):
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._api_url("shop.json"),
                    headers=self._headers(),
                    timeout=10
                )
                return resp.status_code == 200
        except Exception:
            return False
    
    # ── Core operations ───────────────────────────────────────────────────────
    
    async def create_product(self, product: ShopifyProduct) -> DriverResult:
        """Create a new product in the Shopify store."""
        domain, _ = self._get_credentials()
        if not domain:
            return self._error("create_product", "Missing credentials. Run: agentreach shopify set-credentials")
        
        payload = {
            "product": {
                "title": product.title,
                "body_html": product.description,
                "vendor": product.vendor,
                "product_type": product.product_type,
                "tags": ", ".join(product.tags),
                "published": product.published,
                "variants": [{
                    "price": str(product.price),
                    "sku": product.sku,
                    "inventory_quantity": product.inventory_qty,
                }],
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._api_url("products.json"),
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            
            if resp.status_code not in (200, 201):
                return self._error("create_product", f"API error {resp.status_code}: {resp.text}")
            
            data = resp.json()["product"]
            product_id = str(data["id"])
            url = f"https://{domain}/products/{data['handle']}"
            
            # Upload images if provided
            for img_path in product.images[:10]:
                await self._upload_image(client, product_id, img_path)
            
            return self._success(
                "create_product",
                resource_id=product_id,
                url=url,
                message=f"'{product.title}' created on Shopify",
                handle=data["handle"],
            )
    
    async def _upload_image(self, client: httpx.AsyncClient, product_id: str, img_path: str):
        """Upload an image to a product."""
        from pathlib import Path
        import base64
        
        p = Path(img_path)
        if not p.exists():
            return
        
        img_data = base64.b64encode(p.read_bytes()).decode()
        await client.post(
            self._api_url(f"products/{product_id}/images.json"),
            json={"image": {"attachment": img_data, "filename": p.name}},
            headers=self._headers(),
            timeout=60,
        )
    
    async def get_orders(self, limit: int = 50, status: str = "any") -> List[dict]:
        """Fetch recent orders."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._api_url(f"orders.json?limit={limit}&status={status}"),
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("orders", [])
    
    async def update_inventory(self, inventory_item_id: str, location_id: str, qty: int) -> DriverResult:
        """Update inventory level for a variant."""
        payload = {
            "location_id": location_id,
            "inventory_item_id": inventory_item_id,
            "available": qty,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._api_url("inventory_levels/set.json"),
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                return self._success("update_inventory", message=f"Inventory updated to {qty}")
            return self._error("update_inventory", f"API error {resp.status_code}: {resp.text}")
    
    # ── Sync wrappers (for CLI / non-async contexts) ──────────────────────────
    
    def publish_product(self, product: ShopifyProduct) -> DriverResult:
        return asyncio.run(self.create_product(product))
    
    def fetch_orders(self, limit: int = 50) -> List[dict]:
        return asyncio.run(self.get_orders(limit=limit))
```

### 2.3 Testing Harness

Every driver should include a standard test harness. The SDK provides a base test class:

```python
# src/agentreach/testing.py

"""
AgentReach Driver Testing Harness.
Community driver developers: inherit from DriverTestCase in your tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agentreach.drivers.base import BasePlatformDriver, DriverResult


class DriverTestCase:
    """
    Base test class for AgentReach drivers.
    
    Usage:
        class TestShopifyDriver(DriverTestCase):
            driver_class = ShopifyDriver
            platform_name = "shopify"
            
            def test_create_product(self):
                ...
    """
    
    driver_class: type = None
    platform_name: str = None
    
    @pytest.fixture
    def mock_vault(self):
        vault = MagicMock()
        vault.load.return_value = {"access_token": "test_token", "shop_domain": "test.myshopify.com"}
        return vault
    
    @pytest.fixture
    def driver(self, mock_vault):
        return self.driver_class(vault=mock_vault)
    
    def test_has_platform_name(self, driver):
        assert driver.platform_name == self.platform_name
    
    def test_inherits_base(self):
        assert issubclass(self.driver_class, BasePlatformDriver)
    
    def test_has_version(self):
        assert hasattr(self.driver_class, "version")
        assert isinstance(self.driver_class.version, str)
    
    def test_has_capabilities(self):
        assert hasattr(self.driver_class, "capabilities")
        assert isinstance(self.driver_class.capabilities, list)
    
    def test_success_result(self, driver):
        result = driver._success("test_op", resource_id="123", url="https://example.com", message="ok")
        assert result.success is True
        assert result.platform == self.platform_name
        assert result.resource_id == "123"
    
    def test_error_result(self, driver):
        result = driver._error("test_op", "something broke")
        assert result.success is False
        assert result.error == "something broke"
    
    @pytest.mark.asyncio
    async def test_verify_session_defined(self, driver):
        """verify_session must be implemented."""
        # Don't call it (requires live session), just check it's overridden
        assert driver.verify_session is not None
        method = getattr(driver.__class__, "verify_session")
        assert not getattr(method, "__isabstractmethod__", False), \
            "verify_session must be implemented in the driver class"
```

---

## 3. Registry Design

### 3.1 Recommendation: PyPI + GitHub

**Don't build a custom registry.** Use PyPI for distribution and GitHub for discovery, reviews, and quality signaling.

| Concern | Solution |
|---|---|
| Distribution | PyPI — `pip install agentreach-driver-shopify` |
| Discovery | PyPI search + GitHub topic `agentreach-driver` |
| Quality gating | GitHub PR review for "official" drivers |
| Versioning | Semantic versioning via PyPI |
| Official vs community | Namespace prefix (`agentreach-driver-*`) + PyPI org |
| Reviews/ratings | GitHub stars + README badges |

### 3.2 Driver Tiers

**Tier 1 — Core (built-in):** Shipped with AgentReach package. Maintained by the core team. Current: KDP, Etsy, Gumroad, Pinterest, Reddit, Nextdoor, Twitter.

**Tier 2 — Verified:** Published by the core team or vetted contributors. Installable from PyPI under the `agentreach-driver-*` namespace. Must pass quality checks (test coverage, working verify_session, README, versioning).

**Tier 3 — Community:** Anyone can publish as `agentreach-driver-<platform>`. Clearly marked as community. No quality guarantee.

### 3.3 Publishing a Driver

```bash
# 1. Scaffold the driver
agentreach scaffold shopify
cd agentreach-driver-shopify

# 2. Implement the driver (edit src/driver.py)

# 3. Test it
pip install -e ".[dev]"
pytest tests/

# 4. Build and publish to PyPI
python -m build
python -m twine upload dist/*

# 5. Tag the GitHub repo for discovery
# Add topic: agentreach-driver
# Add badge: [![AgentReach Driver](https://img.shields.io/badge/AgentReach-Driver-blue)](https://github.com/topics/agentreach-driver)
```

### 3.4 Version Pinning

AgentReach respects pip version pinning:
```bash
agentreach install shopify                 # latest
agentreach install shopify --version 1.2.0 # pinned
```

For reproducible agent environments, generate a lockfile:
```bash
agentreach lock > agentreach.lock
# agentreach.lock is just pip freeze output filtered to agentreach-driver-* packages
```

### 3.5 Future: Official Registry API

If PyPI-only discovery proves insufficient, a lightweight registry API can be added later:

```
GET https://registry.agentreach.dev/drivers
GET https://registry.agentreach.dev/drivers/{platform}
POST https://registry.agentreach.dev/drivers  (submit for review)
```

This would aggregate PyPI data + GitHub stars + download counts + verified status. Low priority until the ecosystem has 20+ drivers.

---

## 4. Priority Drivers to Build

Ranked by market demand, automation value, and implementation feasibility.

### Tier 1 — Build First (High Impact, API Available)

| Platform | Auth | Key Capabilities | Estimated Effort |
|---|---|---|---|
| **Shopify** | API token | Products, orders, inventory | 3-4 days |
| **Stripe** | API token | Products, payments, subscriptions | 2-3 days |
| **WordPress/WooCommerce** | REST API | Posts, products, media | 3-4 days |
| **YouTube** | OAuth2 | Upload videos, manage channel | 4-5 days |
| **QuickBooks Online** | OAuth2 | Invoices, customers, expenses | 4-5 days |

### Tier 2 — Build Next (High Demand, Harder Auth)

| Platform | Auth | Key Capabilities | Estimated Effort |
|---|---|---|---|
| **LinkedIn** | Browser cookie | Posts, articles, comments | 3-4 days |
| **Instagram** | Browser cookie | Posts, stories, reels | 4-5 days |
| **TikTok** | Browser cookie | Upload videos, manage content | 4-5 days |
| **Amazon Seller Central** | Browser cookie | Listings, FBA inventory | 5-7 days |
| **Twitter/X (upgrade)** | Browser cookie | Already exists — expand to API | 1-2 days |

### Tier 3 — Community (Niche but Valuable)

| Platform | Auth | Key Capabilities |
|---|---|---|
| **Facebook Marketplace** | Browser cookie | Listings, messages |
| **Substack** | Browser cookie | Publish posts, manage subscribers |
| **Medium** | API token | Publish posts |
| **Notion** | API token | Databases, pages |
| **Airtable** | API token | Tables, records |
| **HubSpot** | API token | CRM records, deals, contacts |
| **Mailchimp** | API key | Campaigns, subscribers |
| **Google Business Profile** | OAuth2 | Posts, reviews, hours |
| **Craigslist** | Browser cookie | Post listings |
| **eBay** | API token | Listings, orders |
| **Poshmark** | Browser cookie | Listings, shares |
| **Mercari** | Browser cookie | Listings |

### Implementation Notes by Platform

**Shopify:** Use Admin API v2024-01. Requires custom app with correct scopes: `write_products, read_orders, write_inventory`. Token stored in vault.

**Stripe:** Pure REST API. Easiest driver to write. Key ops: create products, create payment links, retrieve subscription data. No browser needed.

**LinkedIn:** Browser-cookie driver. Hardest part: CSRF token rotation. Use the session.py pattern from existing drivers. Key ops: text post, image post, article publish.

**Instagram:** Browser-cookie driver using instagram.com (not Graph API — requires Business account approval). Key ops: photo upload, caption, hashtags. Reels require video processing pipeline.

**TikTok:** Browser-cookie driver. Video upload flow is the main feature. Playwright must handle the multi-step upload modal.

**YouTube:** OAuth2 via Google APIs. Use the `google-auth` + `google-api-python-client` packages. Key ops: upload video, set title/description/tags/thumbnail.

**WordPress:** REST API at `/wp-json/wp/v2/`. Auth via Application Passwords (built into WP 5.6+). Key ops: create post, upload media, create WooCommerce product.

---

## 5. Skill Packs

Skill packs are pre-built multi-step workflows that orchestrate multiple drivers. They're not drivers — they're higher-level agents that use drivers as tools.

### 5.1 Architecture

```python
# src/agentreach/skills/base.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class SkillResult:
    success: bool
    skill: str
    steps_completed: int = 0
    steps_total: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    summary: str = ""
    
    @property
    def partial_success(self) -> bool:
        return self.steps_completed > 0 and not self.success


class BaseSkill(ABC):
    """
    Base class for skill packs.
    Skills orchestrate multiple drivers to complete multi-step workflows.
    """
    
    skill_name: str = "unknown"
    description: str = ""
    required_drivers: List[str] = []   # Platform names that must be installed+authenticated
    
    def __init__(self, vault=None):
        from agentreach.vault.store import SessionVault
        from agentreach.plugins import get_all_drivers
        self.vault = vault or SessionVault()
        self._drivers: Dict = {}
    
    def _get_driver(self, platform: str):
        if platform not in self._drivers:
            from agentreach.plugins import get_driver
            self._drivers[platform] = get_driver(platform)
        return self._drivers[platform]
    
    def validate_prerequisites(self) -> List[str]:
        """Check all required drivers are installed and have valid sessions."""
        missing = []
        for platform in self.required_drivers:
            try:
                driver = self._get_driver(platform)
                if not driver.check_health():
                    missing.append(f"{platform} (session invalid — run: agentreach harvest {platform})")
            except ValueError:
                missing.append(f"{platform} (not installed — run: agentreach install {platform})")
        return missing
    
    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """Execute the skill. Override this."""
        pass
    
    def run(self, **kwargs) -> SkillResult:
        """Synchronous wrapper."""
        import asyncio
        return asyncio.run(self.execute(**kwargs))
```

### 5.2 Built-In Skill Packs

#### Social Broadcast
```python
# src/agentreach/skills/social_broadcast.py

"""
Skill: Social Broadcast
Post the same content (with platform-appropriate formatting) to all social platforms.
Platforms: Twitter, Reddit, Pinterest, LinkedIn, Instagram, TikTok
"""

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
from .base import BaseSkill, SkillResult


@dataclass
class BroadcastContent:
    text: str
    image_path: Optional[str] = None
    link: Optional[str] = None
    hashtags: List[str] = None
    platforms: List[str] = None   # None = all available


class SocialBroadcastSkill(BaseSkill):
    skill_name = "social_broadcast"
    description = "Post content to all connected social platforms simultaneously"
    required_drivers = ["twitter"]   # Minimum — others are optional
    
    async def execute(self, content: BroadcastContent) -> SkillResult:
        platforms = content.platforms or ["twitter", "reddit", "pinterest", "linkedin", "instagram"]
        results = []
        errors = []
        steps = 0
        
        for platform in platforms:
            try:
                driver = self._get_driver(platform)
                if not driver.check_health():
                    errors.append(f"{platform}: session invalid")
                    continue
                
                # Adapt content per platform
                text = self._adapt_text(platform, content)
                result = await self._post_to_platform(platform, driver, text, content)
                results.append({"platform": platform, "result": result})
                if result.success:
                    steps += 1
                else:
                    errors.append(f"{platform}: {result.error}")
                    
            except Exception as e:
                errors.append(f"{platform}: {e}")
        
        return SkillResult(
            success=len(errors) == 0,
            skill=self.skill_name,
            steps_completed=steps,
            steps_total=len(platforms),
            results=results,
            errors=errors,
            summary=f"Posted to {steps}/{len(platforms)} platforms"
        )
    
    def _adapt_text(self, platform: str, content: BroadcastContent) -> str:
        """Adapt content for each platform's constraints."""
        text = content.text
        hashtags = content.hashtags or []
        link = content.link or ""
        
        if platform == "twitter":
            # 280 char limit, include hashtags inline
            tags = " ".join(f"#{h}" for h in hashtags[:3])
            full = f"{text}\n{link}\n{tags}".strip()
            return full[:280]
        
        elif platform == "reddit":
            # No hashtags, add link if present
            return f"{text}\n\n{link}".strip() if link else text
        
        elif platform in ("linkedin", "instagram"):
            # Full text + hashtags at end
            tags = " ".join(f"#{h}" for h in hashtags)
            return f"{text}\n\n{link}\n\n{tags}".strip()
        
        elif platform == "pinterest":
            return text[:500]   # Pinterest description limit
        
        return text
    
    async def _post_to_platform(self, platform, driver, text, content):
        if platform == "twitter":
            return await driver.tweet(text)
        elif platform == "pinterest" and content.image_path:
            from agentreach_driver_pinterest import PinterestPin
            pin = PinterestPin(title="", description=text, image_path=content.image_path, link=content.link or "")
            return await driver.post_pin(pin)
        elif hasattr(driver, "post"):
            return await driver.post(text)
        elif hasattr(driver, "post_content"):
            return await driver.post_content(text, image_path=content.image_path)
        else:
            from agentreach.drivers.base import DriverResult
            return DriverResult(success=False, platform=platform, error="Driver doesn't support post_content")
```

#### Cross-List Products
```python
# src/agentreach/skills/cross_list.py

"""
Skill: Cross-List Products
Take a product definition and list it on multiple e-commerce platforms simultaneously.
Platforms: Etsy, Gumroad, Shopify, eBay, Amazon Seller Central
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .base import BaseSkill, SkillResult


@dataclass 
class UniversalProduct:
    title: str
    description: str
    price: float
    images: List[str] = field(default_factory=list)
    digital_file: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    platforms: List[str] = None   # None = all available e-commerce drivers


class CrossListSkill(BaseSkill):
    skill_name = "cross_list"
    description = "List a product on all connected e-commerce platforms"
    required_drivers = []  # At least one e-commerce driver
    
    ECOMMERCE_PLATFORMS = ["etsy", "gumroad", "shopify", "ebay", "amazon_seller"]
    
    async def execute(self, product: UniversalProduct) -> SkillResult:
        platforms = product.platforms or self.ECOMMERCE_PLATFORMS
        results = []
        errors = []
        steps = 0
        
        for platform in platforms:
            try:
                driver = self._get_driver(platform)
                if not driver.check_health():
                    continue   # Skip platforms without valid sessions — not an error
                
                result = await self._list_on_platform(platform, driver, product)
                results.append({"platform": platform, "result": result, "url": result.url})
                if result.success:
                    steps += 1
                else:
                    errors.append(f"{platform}: {result.error}")
                    
            except ValueError:
                pass   # Driver not installed — skip silently
            except Exception as e:
                errors.append(f"{platform}: {e}")
        
        return SkillResult(
            success=steps > 0,
            skill=self.skill_name,
            steps_completed=steps,
            steps_total=len(platforms),
            results=results,
            errors=errors,
            summary=f"Listed on {steps} platform(s): {[r['platform'] for r in results if r['result'].success]}"
        )
    
    async def _list_on_platform(self, platform, driver, product):
        if platform == "etsy":
            from agentreach.drivers.etsy import EtsyListing
            listing = EtsyListing(
                title=product.title,
                description=product.description,
                price=product.price,
                tags=product.tags[:13],
                image_paths=product.images,
                digital_files=[product.digital_file] if product.digital_file else [],
            )
            return await driver.create_listing(listing)
        
        elif platform == "gumroad":
            from agentreach.drivers.gumroad import GumroadProduct
            p = GumroadProduct(
                name=product.title,
                description=product.description,
                price_cents=int(product.price * 100),
                file_path=product.digital_file,
            )
            return await driver.create_product(p)
        
        elif platform == "shopify":
            from agentreach_driver_shopify import ShopifyProduct
            p = ShopifyProduct(
                title=product.title,
                description=product.description,
                price=product.price,
                tags=product.tags,
                images=product.images,
            )
            return await driver.create_product(p)
        
        elif hasattr(driver, "create_listing"):
            return await driver.create_listing(product)
        elif hasattr(driver, "publish_product"):
            return await driver.publish_product(product)
        else:
            from agentreach.drivers.base import DriverResult
            return DriverResult(success=False, platform=platform, error="No listing method found on driver")
```

#### Inventory Sync
```python
# src/agentreach/skills/inventory_sync.py

"""
Skill: Inventory Sync
Keep inventory levels in sync across all connected store platforms.
"""

from .base import BaseSkill, SkillResult

class InventorySyncSkill(BaseSkill):
    skill_name = "inventory_sync"
    description = "Sync inventory levels across all connected e-commerce platforms"
    
    async def execute(self, sku: str, quantity: int, source_platform: str = "shopify") -> SkillResult:
        """
        Set inventory qty for a SKU on all connected platforms.
        source_platform is the source of truth.
        """
        INVENTORY_PLATFORMS = ["shopify", "ebay", "etsy", "amazon_seller"]
        results = []
        steps = 0
        errors = []
        
        for platform in INVENTORY_PLATFORMS:
            if platform == source_platform:
                continue
            try:
                driver = self._get_driver(platform)
                if not driver.check_health():
                    continue
                if hasattr(driver, "update_inventory"):
                    result = await driver.update_inventory(sku=sku, quantity=quantity)
                    if result.success:
                        steps += 1
                    else:
                        errors.append(f"{platform}: {result.error}")
                    results.append({"platform": platform, "result": result})
            except Exception as e:
                errors.append(f"{platform}: {e}")
        
        return SkillResult(
            success=len(errors) == 0,
            skill=self.skill_name,
            steps_completed=steps,
            steps_total=len(INVENTORY_PLATFORMS) - 1,
            results=results,
            errors=errors,
            summary=f"Synced inventory ({sku}={quantity}) to {steps} platforms"
        )
```

### 5.3 CLI for Skills

```python
# Added to cli.py

skills_app = typer.Typer(help="Multi-platform workflow skills")
app.add_typer(skills_app, name="skill")

@skills_app.command("broadcast")
def skill_broadcast(
    text: str = typer.Argument(..., help="Content to broadcast"),
    image: Optional[Path] = typer.Option(None, help="Optional image to attach"),
    link: str = typer.Option("", help="Link to include"),
    hashtags: str = typer.Option("", help="Comma-separated hashtags"),
    platforms: str = typer.Option("", help="Comma-separated platforms (default: all)"),
):
    """Broadcast content to all connected social platforms."""
    from .skills.social_broadcast import SocialBroadcastSkill, BroadcastContent
    
    content = BroadcastContent(
        text=text,
        image_path=str(image) if image else None,
        link=link,
        hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
        platforms=[p.strip() for p in platforms.split(",") if p.strip()] or None,
    )
    
    skill = SocialBroadcastSkill()
    result = skill.run(content=content)
    
    if result.success:
        rprint(f"[green]✅ {result.summary}[/green]")
    else:
        rprint(f"[yellow]⚠️  {result.summary}[/yellow]")
    
    for r in result.results:
        status = "✅" if r["result"].success else "❌"
        rprint(f"  {status} {r['platform']}: {r['result'].url or r['result'].message or r['result'].error}")


@skills_app.command("cross-list")
def skill_cross_list(
    title: str = typer.Option(..., help="Product title"),
    description: str = typer.Option(..., help="Product description"),
    price: float = typer.Option(..., help="Price in USD"),
    file: Optional[Path] = typer.Option(None, help="Digital file path"),
    images: str = typer.Option("", help="Comma-separated image paths"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    platforms: str = typer.Option("", help="Comma-separated platforms (default: all e-commerce)"),
):
    """Cross-list a product on all connected e-commerce platforms."""
    from .skills.cross_list import CrossListSkill, UniversalProduct
    
    product = UniversalProduct(
        title=title,
        description=description,
        price=price,
        digital_file=str(file) if file else None,
        images=[i.strip() for i in images.split(",") if i.strip()],
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        platforms=[p.strip() for p in platforms.split(",") if p.strip()] or None,
    )
    
    skill = CrossListSkill()
    result = skill.run(product=product)
    
    rprint(f"[bold]{'✅' if result.success else '⚠️'} {result.summary}[/bold]")
    for r in result.results:
        status = "✅" if r["result"].success else "❌"
        url = r.get("url", "")
        rprint(f"  {status} {r['platform']}{': ' + url if url else ''}")
```

---

## 6. LangChain / CrewAI / AutoGen Integration

### 6.1 Design Philosophy

Each framework wants tools in a different shape. AgentReach provides thin wrappers that adapt drivers into each framework's tool interface. The core driver code doesn't change — only the wrapper shape.

### 6.2 LangChain Integration

```python
# src/agentreach/integrations/langchain.py

"""
AgentReach × LangChain Integration
Wraps drivers as LangChain Tools for use in chains and agents.

Usage:
    from agentreach.integrations.langchain import AgentReachToolkit
    from langchain.agents import initialize_agent, AgentType
    
    toolkit = AgentReachToolkit(platforms=["twitter", "etsy", "gumroad"])
    tools = toolkit.get_tools()
    
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    )
    agent.run("Post a tweet about our new product launch")
"""

from typing import List, Optional, Any


def create_langchain_tool(driver, method_name: str, description: str):
    """
    Wrap a driver method as a LangChain StructuredTool.
    Lazy import: only requires langchain if this function is called.
    """
    try:
        from langchain.tools import StructuredTool
        import inspect
        
        method = getattr(driver, method_name)
        sig = inspect.signature(method)
        
        # Build Pydantic schema from method signature
        from pydantic import create_model
        fields = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)
        
        ArgsSchema = create_model(f"{method_name}_args", **fields)
        
        def run_method(**kwargs):
            import asyncio
            if asyncio.iscoroutinefunction(method):
                result = asyncio.run(method(**kwargs))
            else:
                result = method(**kwargs)
            if hasattr(result, "success"):
                if result.success:
                    return result.message or result.url or f"Success: {result.resource_id}"
                else:
                    return f"Error: {result.error}"
            return str(result)
        
        return StructuredTool(
            name=f"{driver.platform_name}_{method_name}",
            description=description,
            func=run_method,
            args_schema=ArgsSchema,
        )
    
    except ImportError:
        raise ImportError("langchain is required: pip install langchain")


class AgentReachToolkit:
    """
    LangChain Toolkit wrapping AgentReach drivers.
    Auto-discovers all installed drivers and exposes their capabilities as tools.
    """
    
    # Capability → (method_name, description) mapping
    CAPABILITY_MAP = {
        "tweet": ("tweet", "Post a tweet to X/Twitter. Input: text (string, max 280 chars)"),
        "post_pin": ("post_pin", "Post a pin to Pinterest. Input: title, description, image_path, link"),
        "create_listing": ("create_listing", "Create a new product listing. Input: title, description, price, tags"),
        "publish_product": ("publish_product", "Publish a product for sale. Input: product details"),
        "post": ("post", "Post content to the platform. Input: text content"),
        "comment": ("comment", "Post a comment. Input: url, text"),
    }
    
    def __init__(
        self, 
        platforms: Optional[List[str]] = None,
        vault=None
    ):
        from agentreach.plugins import get_all_drivers
        
        all_drivers = get_all_drivers()
        
        if platforms:
            self.drivers = {p: all_drivers[p](vault=vault) for p in platforms if p in all_drivers}
        else:
            self.drivers = {name: cls(vault=vault) for name, cls in all_drivers.items()}
    
    def get_tools(self) -> List:
        """Return list of LangChain Tool objects for all available driver methods."""
        tools = []
        for platform, driver in self.drivers.items():
            if not driver.check_health():
                continue
            for method_name, description in self.CAPABILITY_MAP.items():
                if hasattr(driver, method_name):
                    tool = create_langchain_tool(driver, method_name, description[1])
                    tools.append(tool)
        return tools
```

### 6.3 CrewAI Integration

```python
# src/agentreach/integrations/crewai.py

"""
AgentReach × CrewAI Integration
Wraps drivers as CrewAI tools for use in crews.

Usage:
    from crewai import Agent, Task, Crew
    from agentreach.integrations.crewai import agentreach_tools
    
    tools = agentreach_tools(platforms=["twitter", "etsy"])
    
    social_agent = Agent(
        role="Social Media Manager",
        goal="Promote our products across all platforms",
        tools=tools["twitter"],
    )
"""

from typing import List, Dict, Optional


def create_crewai_tool(driver, method_name: str, tool_name: str, description: str):
    """Wrap a driver method as a CrewAI BaseTool."""
    try:
        from crewai.tools import BaseTool
        from pydantic import BaseModel, Field
        import inspect
        
        method = getattr(driver, method_name)
        
        class DriverTool(BaseTool):
            name: str = tool_name
            description: str = description
            
            def _run(self, *args, **kwargs) -> str:
                import asyncio
                if asyncio.iscoroutinefunction(method):
                    result = asyncio.run(method(*args, **kwargs))
                else:
                    result = method(*args, **kwargs)
                
                if hasattr(result, "success"):
                    return result.message or result.url or ("Success" if result.success else f"Error: {result.error}")
                return str(result)
        
        return DriverTool()
    
    except ImportError:
        raise ImportError("crewai is required: pip install crewai")


def agentreach_tools(
    platforms: Optional[List[str]] = None,
    vault=None
) -> Dict[str, List]:
    """
    Return CrewAI tools organized by platform.
    
    Returns:
        Dict of {platform_name: [tool1, tool2, ...]}
    """
    from agentreach.plugins import get_all_drivers
    
    TOOL_CONFIG = [
        ("tweet", "twitter_tweet", "Post a tweet to X/Twitter"),
        ("post", "platform_post", "Post content to the platform"),
        ("create_listing", "create_listing", "Create a new product listing"),
        ("comment", "post_comment", "Post a comment on content"),
        ("get_orders", "get_orders", "Retrieve recent orders"),
    ]
    
    all_drivers = get_all_drivers()
    result = {}
    
    target_platforms = platforms or list(all_drivers.keys())
    
    for platform in target_platforms:
        if platform not in all_drivers:
            continue
        driver = all_drivers[platform](vault=vault)
        if not driver.check_health():
            continue
        
        platform_tools = []
        for method_name, tool_name, description in TOOL_CONFIG:
            if hasattr(driver, method_name):
                tool_name_full = f"{platform}_{tool_name}"
                tool = create_crewai_tool(driver, method_name, tool_name_full, description)
                platform_tools.append(tool)
        
        if platform_tools:
            result[platform] = platform_tools
    
    return result
```

### 6.4 AutoGen Integration

```python
# src/agentreach/integrations/autogen.py

"""
AgentReach × AutoGen Integration
Wraps drivers as AutoGen function tools for ConversableAgent.

Usage:
    from autogen import ConversableAgent
    from agentreach.integrations.autogen import register_agentreach_tools
    
    agent = ConversableAgent("social_agent", llm_config=llm_config)
    register_agentreach_tools(agent, platforms=["twitter", "etsy"])
    
    # Now the agent can call agentreach tools natively
"""

from typing import List, Optional, Callable


def register_agentreach_tools(
    agent,
    platforms: Optional[List[str]] = None,
    executor_agent=None,
    vault=None,
) -> List[str]:
    """
    Register AgentReach driver methods as AutoGen tools on an agent.
    Returns list of registered tool names.
    
    Args:
        agent: The AutoGen ConversableAgent to register tools on
        platforms: Platforms to expose (None = all available)
        executor_agent: Agent to execute tools (if using executor pattern)
        vault: Optional SessionVault override
    """
    from agentreach.plugins import get_all_drivers
    import inspect
    
    all_drivers = get_all_drivers()
    registered = []
    
    METHODS_TO_EXPOSE = {
        "tweet": "Post a tweet to X/Twitter",
        "post": "Post content to the platform",
        "create_listing": "Create a new product listing",
        "comment": "Post a comment",
        "verify_session": "Check if the platform session is valid",
    }
    
    target_platforms = platforms or list(all_drivers.keys())
    
    for platform in target_platforms:
        if platform not in all_drivers:
            continue
        driver = all_drivers[platform](vault=vault)
        
        for method_name, description in METHODS_TO_EXPOSE.items():
            if not hasattr(driver, method_name):
                continue
            
            method = getattr(driver, method_name)
            tool_name = f"{platform}_{method_name}"
            
            # Create a closure to capture driver + method
            def make_tool_func(d, m, mn):
                import asyncio
                def tool_func(**kwargs):
                    if asyncio.iscoroutinefunction(m):
                        result = asyncio.run(m(**kwargs))
                    else:
                        result = m(**kwargs)
                    if hasattr(result, "success"):
                        return {"success": result.success, "message": result.message, "url": result.url, "error": result.error}
                    return result
                tool_func.__name__ = f"{d.platform_name}_{mn}"
                tool_func.__doc__ = f"{description} on {d.platform_name}"
                return tool_func
            
            tool_func = make_tool_func(driver, method, method_name)
            
            # Register with AutoGen
            try:
                if executor_agent:
                    agent.register_for_llm(name=tool_name, description=description)(tool_func)
                    executor_agent.register_for_execution(name=tool_name)(tool_func)
                else:
                    agent.register_for_llm(name=tool_name, description=description)(tool_func)
                registered.append(tool_name)
            except Exception as e:
                pass   # AutoGen version differences — skip silently
    
    return registered
```

### 6.5 Generic Tool Protocol (Framework-Agnostic)

For frameworks not listed above, or for building custom agents:

```python
# src/agentreach/integrations/tools.py

"""
AgentReach Tool Protocol
Framework-agnostic tool definitions for any agent system.
Returns simple dicts that any framework can consume.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class AgentReachTool:
    """Framework-agnostic tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]   # JSON Schema
    platform: str
    method: str
    callable: Any   # The actual function to call


def get_tools_as_openai_functions(platforms: List[str] = None) -> List[Dict]:
    """
    Return all available tools as OpenAI function definitions.
    Compatible with OpenAI, Anthropic tool_use, and any framework that accepts this format.
    """
    from agentreach.plugins import get_all_drivers
    import inspect
    
    all_drivers = get_all_drivers()
    functions = []
    
    target = platforms or list(all_drivers.keys())
    
    for platform in target:
        if platform not in all_drivers:
            continue
        driver = all_drivers[platform]()
        if not driver.check_health():
            continue
        
        for method_name in dir(driver):
            if method_name.startswith("_"):
                continue
            method = getattr(driver, method_name)
            if not callable(method):
                continue
            if not getattr(method, "__doc__", None):
                continue
            
            sig = inspect.signature(method)
            params = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                params[param_name] = {"type": "string", "description": param_name}
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            
            functions.append({
                "name": f"{platform}_{method_name}",
                "description": f"[{platform}] {method.__doc__.strip().split(chr(10))[0]}",
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required,
                }
            })
    
    return functions
```

### 6.6 Quick Start Examples Per Framework

#### LangChain
```python
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from agentreach.integrations.langchain import AgentReachToolkit

llm = ChatOpenAI(model="gpt-4", temperature=0)
toolkit = AgentReachToolkit(platforms=["twitter", "etsy", "gumroad"])
tools = toolkit.get_tools()

agent = initialize_agent(
    tools=tools, llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

agent.run("Post a tweet saying 'New digital journal just dropped on Etsy!' and create the listing if not already up")
```

#### CrewAI
```python
from crewai import Agent, Task, Crew
from agentreach.integrations.crewai import agentreach_tools

tools = agentreach_tools(platforms=["twitter", "etsy"])

marketer = Agent(
    role="Digital Marketing Specialist",
    goal="Maximize product visibility across platforms",
    backstory="Expert at multi-platform content strategy",
    tools=tools.get("twitter", []) + tools.get("etsy", []),
)

task = Task(
    description="Tweet about our new Etsy listing and check that the session is valid",
    agent=marketer,
)

crew = Crew(agents=[marketer], tasks=[task])
crew.kickoff()
```

#### AutoGen
```python
import autogen
from agentreach.integrations.autogen import register_agentreach_tools

config_list = [{"model": "gpt-4", "api_key": "YOUR_KEY"}]

assistant = autogen.ConversableAgent(
    "publishing_assistant",
    llm_config={"config_list": config_list},
)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

registered = register_agentreach_tools(assistant, user_proxy, platforms=["etsy", "gumroad"])
print(f"Registered tools: {registered}")

user_proxy.initiate_chat(
    assistant,
    message="Publish my new PDF guide 'Morning Routine 101' on Gumroad for $9.99"
)
```

---

## 7. Implementation Roadmap

### Phase 1 — Foundation (Week 1-2)
- [ ] Add `plugins.py` with `discover_drivers()` and `get_all_drivers()`
- [ ] Update `drivers/__init__.py` to use plugin loader
- [ ] Add `scaffold_driver()` to generate driver templates
- [ ] Add CLI commands: `install`, `uninstall`, `search`, `scaffold`, `list-drivers`
- [ ] Enhance `BasePlatformDriver` with metadata, capabilities, lifecycle hooks
- [ ] Add `agentreach/testing.py` base test harness
- [ ] Write and publish `agentreach-driver-shopify` on PyPI as reference impl

### Phase 2 — Skill Packs (Week 3)
- [ ] Add `skills/base.py` with `BaseSkill` and `SkillResult`
- [ ] Implement `SocialBroadcastSkill`
- [ ] Implement `CrossListSkill`
- [ ] Implement `InventorySyncSkill`
- [ ] Add `skill broadcast`, `skill cross-list` CLI commands

### Phase 3 — Framework Integrations (Week 4)
- [ ] LangChain wrapper (`integrations/langchain.py`)
- [ ] CrewAI wrapper (`integrations/crewai.py`)
- [ ] AutoGen wrapper (`integrations/autogen.py`)
- [ ] Generic OpenAI functions schema (`integrations/tools.py`)
- [ ] Add optional dependencies to pyproject.toml: `[project.optional-dependencies] langchain = ["langchain>=0.1.0"]`

### Phase 4 — Priority Drivers (Weeks 5-8)
- [ ] `agentreach-driver-shopify` (already planned for Phase 1)
- [ ] `agentreach-driver-stripe`
- [ ] `agentreach-driver-wordpress`
- [ ] `agentreach-driver-youtube`
- [ ] `agentreach-driver-linkedin`

### Phase 5 — Community Launch
- [ ] Publish driver development guide to docs/
- [ ] Add GitHub topic `agentreach-driver` guidelines
- [ ] Create `agentreach-driver-template` repo on GitHub
- [ ] Launch on GitHub Discussions + relevant communities

---

## Appendix: File Structure After Implementation

```
agentreach/
├── src/agentreach/
│   ├── plugins.py              # NEW: plugin discovery, scaffold
│   ├── testing.py              # NEW: DriverTestCase base class
│   ├── drivers/
│   │   ├── base.py             # ENHANCED: metadata, capabilities, lifecycle
│   │   └── [existing drivers]
│   ├── skills/
│   │   ├── __init__.py         # NEW
│   │   ├── base.py             # NEW: BaseSkill, SkillResult
│   │   ├── social_broadcast.py # NEW
│   │   ├── cross_list.py       # NEW
│   │   └── inventory_sync.py   # NEW
│   └── integrations/
│       ├── __init__.py         # NEW
│       ├── langchain.py        # NEW
│       ├── crewai.py           # NEW
│       ├── autogen.py          # NEW
│       └── tools.py            # NEW: generic OpenAI function schema
```

---

*AgentReach — the single layer between any agent and any platform.*

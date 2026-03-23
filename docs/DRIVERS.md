# Building a Custom Platform Driver

This guide walks through adding a new platform driver to AgentReach. By the end you'll have a working driver that integrates with the CLI, vault, health system, and session harvester.

---

## Prerequisites

- Familiarity with `async/await` in Python
- Playwright basics (selectors, page navigation)
- AgentReach installed in dev mode: `pip install -e ".[dev]"`

---

## Step 1: Understand the Driver Contract

Every driver must:

1. Extend `BasePlatformDriver`
2. Define `platform_name` as a class attribute
3. Implement `async def verify_session(self) -> bool`
4. Load the session from the vault before using it
5. Return `UploadResult` (or a similar dataclass) from action methods

The base class handles health checking and the vault connection for you.

---

## Step 2: Decide Your Auth Model

Two patterns exist in AgentReach:

**Browser session (cookie-based):**
- User logs in via `agentreach harvest <platform>`
- Harvester captures cookies automatically via URL pattern detection
- Your driver loads cookies into a headless context via `platform_context()`
- Use this for: KDP, Pinterest, Reddit, Twitter, Nextdoor

**API token:**
- User provides a token via a `set-token` or `set-credentials` CLI command
- Token is stored directly in the vault as JSON
- Your driver reads the token from the vault and uses it in HTTP requests
- Use this for: Etsy, Gumroad

---

## Step 3: Register the Platform

**In `src/agentreach/drivers/__init__.py`:**

```python
from .myplatform import MyPlatformDriver

DRIVERS = {
    # existing drivers...
    "myplatform": MyPlatformDriver,
}
```

**In `src/agentreach/cli.py`:**

```python
# Add to PLATFORM_META
PLATFORM_META = {
    # existing...
    "myplatform": {"icon": "🌐", "label": "My Platform"},
}

# Create a sub-app
myplatform_app = typer.Typer(help="My Platform commands")
app.add_typer(myplatform_app, name="myplatform")
```

**In `src/agentreach/vault/health.py`:**

```python
PLATFORM_TTL_DAYS = {
    # existing...
    "myplatform": 30,   # adjust based on actual session lifetime
}
```

**In `src/agentreach/browser/harvester.py`:**

Add your platform's post-login URL pattern to the `PLATFORM_PATTERNS` dict:

```python
PLATFORM_PATTERNS = {
    # existing...
    "myplatform": "/dashboard",  # URL fragment that appears after login
}
```

---

## Step 4: Write the Driver

### Browser-based template

```python
"""
AgentReach — My Platform Driver
Browser-based automation via harvested session cookies.

Selectors verified: [DATE - update when you verify them]
"""

import asyncio
from pathlib import Path
from typing import Optional

from .base import BasePlatformDriver, UploadResult
from ..browser.session import platform_context


class MyPlatformPost:
    """Data for a platform post."""
    def __init__(self, title: str, body: str, image_path: Optional[Path] = None):
        self.title = title
        self.body = body
        self.image_path = image_path


class MyPlatformDriver(BasePlatformDriver):

    platform_name = "myplatform"

    async def verify_session(self) -> bool:
        """
        Load the session and check a page that requires authentication.
        Return True only if we're actually logged in.
        """
        session = self.vault.load(self.platform_name)
        if not session:
            return False

        try:
            async with await platform_context(self.platform_name, self.vault) as context:
                page = await context.new_page()
                await page.goto("https://myplatform.com/home", timeout=30000)

                # Check for an element that only appears when logged in
                # e.g., the user avatar, a "New Post" button, etc.
                logged_in = await page.locator("[data-testid='user-menu']").count() > 0
                await context.close()
                return logged_in
        except Exception:
            return False

    def post(self, content: MyPlatformPost) -> UploadResult:
        """Create a post. Synchronous wrapper — called from CLI."""
        return asyncio.run(self._post_async(content))

    async def _post_async(self, content: MyPlatformPost) -> UploadResult:
        """The actual async browser automation."""
        try:
            async with await platform_context(self.platform_name, self.vault) as context:
                page = await context.new_page()

                # Navigate to the post creation page
                await page.goto("https://myplatform.com/new-post", timeout=30000)
                await page.wait_for_load_state("domcontentloaded")

                # Fill the title field
                # NOTE: update this selector date when you verify it still works
                # Selector verified: [DATE]
                await page.locator("#post-title").fill(content.title)

                # Fill the body
                await page.locator("[data-testid='post-body']").fill(content.body)

                # Submit
                await page.locator("button[type='submit']").click()
                await page.wait_for_url("**/post/**", timeout=15000)

                post_url = page.url
                await context.close()

                return UploadResult(
                    success=True,
                    platform=self.platform_name,
                    url=post_url,
                    message=f"Posted to {self.platform_name}",
                )

        except Exception as e:
            return UploadResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
                message=f"Failed to post: {e}",
            )
```

### API token template

```python
"""
AgentReach — My Platform Driver
API-based integration using stored OAuth token.
"""

import asyncio
import httpx
from typing import Optional

from .base import BasePlatformDriver, UploadResult


class MyPlatformDriver(BasePlatformDriver):

    platform_name = "myplatform"
    BASE_URL = "https://api.myplatform.com/v2"

    def save_token(self, token: str) -> None:
        """Store API token in vault. Called by CLI set-token command."""
        from datetime import datetime, timezone
        self.vault.save(self.platform_name, {
            "access_token": token,
            "harvested_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"✅ {self.platform_name} token saved.")

    def _get_token(self) -> str:
        """Load token from vault. Raise if not found."""
        session = self.vault.load(self.platform_name)
        if not session or "access_token" not in session:
            raise RuntimeError(f"No {self.platform_name} token. Run: agentreach {self.platform_name} set-token YOUR_TOKEN")
        return session["access_token"]

    async def verify_session(self) -> bool:
        """Make an authenticated API call to verify the token is valid."""
        try:
            token = self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                return resp.status_code == 200
        except Exception:
            return False

    def create_item(self, name: str, price: float) -> UploadResult:
        """Create an item via the API."""
        return asyncio.run(self._create_item_async(name, price))

    async def _create_item_async(self, name: str, price: float) -> UploadResult:
        try:
            token = self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.BASE_URL}/items",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"name": name, "price": int(price * 100)},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return UploadResult(
                    success=True,
                    platform=self.platform_name,
                    product_id=data.get("id"),
                    url=data.get("url"),
                    message=f"Created '{name}'",
                )
        except httpx.HTTPStatusError as e:
            return UploadResult(
                success=False,
                platform=self.platform_name,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
                message="API request failed",
            )
        except Exception as e:
            return UploadResult(
                success=False,
                platform=self.platform_name,
                error=str(e),
                message="Request failed",
            )
```

---

## Step 5: Add CLI Commands

```python
# In cli.py

myplatform_app = typer.Typer(help="My Platform commands")
app.add_typer(myplatform_app, name="myplatform")

@myplatform_app.command("post")
def myplatform_post(
    title: str = typer.Option(..., help="Post title"),
    body: str = typer.Option(..., help="Post body"),
):
    """Create a post on My Platform."""
    from .drivers.myplatform import MyPlatformDriver, MyPlatformPost

    content = MyPlatformPost(title=title, body=body)

    console.print(f"[bold]🌐 Posting to My Platform...[/bold]")
    driver = MyPlatformDriver()
    driver.require_valid_session()
    result = driver.post(content)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
        if result.url:
            rprint(f"   URL: {result.url}")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)
```

---

## Step 6: Test It

Write a test using a mocked vault and a mocked Playwright context:

```python
# tests/test_myplatform.py
import pytest
from unittest.mock import MagicMock, patch
from agentreach.drivers.myplatform import MyPlatformDriver


def test_verify_session_returns_false_when_no_session():
    """Driver returns False when vault has no session."""
    mock_vault = MagicMock()
    mock_vault.load.return_value = None

    driver = MyPlatformDriver(vault=mock_vault)
    result = asyncio.run(driver.verify_session())
    assert result is False


def test_verify_session_returns_true_when_logged_in():
    """Driver returns True when page shows logged-in indicator."""
    mock_vault = MagicMock()
    mock_vault.load.return_value = {"cookies": [], "harvested_at": "..."}

    with patch("agentreach.drivers.myplatform.platform_context") as mock_ctx:
        # Set up mock page that shows a logged-in selector
        mock_page = MagicMock()
        mock_page.locator.return_value.count = MagicMock(return_value=1)
        # ... configure mock_ctx to return mock_page
        pass

    # This is the test pattern — adapt to your selector
```

---

## Selector Maintenance

Browser selectors break when platforms update their UI. Follow this convention used in `kdp.py`:

```python
# Selector verified: 2026-03-23
# KDP bookshelf listing container
BOOKSHELF_ROW_SELECTOR = ".kpub-title-name"
```

Add the verification date as a comment next to every selector. When a selector breaks, update the comment date when you fix it. This creates an audit trail and helps estimate maintenance frequency.

---

## Checklist Before Merging

- [ ] `platform_name` matches the key in `DRIVERS`, `PLATFORM_META`, and `PLATFORM_TTL_DAYS`
- [ ] `verify_session()` is implemented and actually makes a live request
- [ ] All selectors have verification date comments
- [ ] `require_valid_session()` is called at the top of CLI commands
- [ ] Action methods return `UploadResult` (or a consistent dataclass)
- [ ] Exceptions are caught and returned as `UploadResult(success=False, error=...)`
- [ ] At minimum one test exists for the happy path
- [ ] `PLATFORM_TTL_DAYS` has a sensible TTL for the platform
- [ ] Harvester URL pattern is defined (if browser-based)
- [ ] CHANGELOG.md is updated

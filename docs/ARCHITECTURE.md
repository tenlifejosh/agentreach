# AgentReach — Architecture

Technical reference for contributors and integrators.

---

## Overview

AgentReach is a local Python library and CLI that gives AI agents authenticated access to web platforms. It has three distinct layers:

1. **Session Vault** — encrypted at-rest storage for cookies and API tokens
2. **Browser Layer** — session harvesting (visible browser) and headless session replay
3. **Platform Drivers** — platform-specific automation built on top of the browser layer

These layers compose to give you: *harvest once → automate forever*.

---

## Project Structure

```
agentreach/
├── src/agentreach/
│   ├── __init__.py            # Package version (0.3.0)
│   ├── cli.py                 # Typer CLI — all commands
│   │
│   ├── vault/
│   │   ├── store.py           # SessionVault — AES-128-CBC (Fernet) encrypted storage
│   │   ├── health.py          # SessionHealth — TTL-based expiry detection
│   │   └── monitor.py         # Session categorization + status bucketing
│   │
│   ├── browser/
│   │   ├── harvester.py       # Cookie harvest via visible browser
│   │   ├── session.py         # Load sessions into headless context
│   │   └── uploader.py        # React-bypass file upload engine
│   │
│   └── drivers/
│       ├── __init__.py        # Driver registry + get_driver()
│       ├── base.py            # BasePlatformDriver ABC
│       ├── kdp.py             # Amazon KDP (browser automation)
│       ├── etsy.py            # Etsy (API + browser for uploads)
│       ├── gumroad.py         # Gumroad (API + browser for product creation)
│       ├── pinterest.py       # Pinterest (browser automation)
│       ├── reddit.py          # Reddit (browser automation)
│       ├── twitter.py         # X/Twitter (browser automation)
│       └── nextdoor.py        # Nextdoor (browser automation)
│
├── tests/
│   └── test_vault.py          # Vault unit tests
│
└── pyproject.toml
```

---

## Layer 1: Session Vault

**Location:** `src/agentreach/vault/`

### `store.py` — SessionVault

The vault is a directory of encrypted JSON files at `~/.agentreach/vault/`. Each platform gets its own `.vault` file.

```
~/.agentreach/vault/
├── kdp.vault          # Playwright cookies for amazon.com
├── etsy.vault         # Etsy API key + OAuth token + shop ID
├── gumroad.vault      # Gumroad API access token
├── pinterest.vault    # Playwright cookies for pinterest.com
└── reddit.vault       # Playwright cookies for reddit.com
```

**Key derivation:**
```python
machine_id = str(uuid.getnode()).encode()   # MAC address as integer → bytes
salt = hashlib.sha256(machine_id).digest()  # 32-byte deterministic salt
kdf = PBKDF2HMAC(SHA256, length=32, salt=salt, iterations=480000)
key = base64.urlsafe_b64encode(kdf.derive(machine_id))
```

Key is derived at module import time and cached as `_FERNET`. All vault files are encrypted with this same key. Vault files are non-portable — they can only be decrypted on the machine that created them.

**Encryption:** Python `cryptography` library's `Fernet` — AES-256-CBC + HMAC-SHA256 with a random IV per write.

**Data format:** Each `.vault` file is a Fernet-encrypted JSON blob. Example plaintext:
```json
{
  "cookies": [
    {"name": "session-id", "value": "...", "domain": ".amazon.com", ...}
  ],
  "harvested_at": "2026-03-15T10:23:44+00:00",
  "_saved_at": "2026-03-15T10:23:44.123456+00:00"
}
```

API-based platforms (Etsy, Gumroad) store token data instead of cookies:
```json
{
  "api_key": "...",
  "access_token": "...",
  "shop_id": "...",
  "harvested_at": "2026-03-15T10:23:44+00:00",
  "_saved_at": "2026-03-15T10:23:44.123456+00:00"
}
```

### `health.py` — Session Health Checking

Health is determined by comparing `harvested_at` against known TTL estimates per platform:

```python
PLATFORM_TTL_DAYS = {
    "kdp":       30,
    "etsy":      60,
    "gumroad":   90,
    "pinterest": 30,
    "nextdoor":  30,
}
DEFAULT_TTL_DAYS = 30   # reddit, twitter fall through to this
```

**SessionStatus enum:**
- `HEALTHY` — has a session, within TTL
- `EXPIRING_SOON` — within 7 days of estimated expiry
- `EXPIRED` — past estimated TTL
- `MISSING` — no vault file exists
- `UNKNOWN` — vault file exists but no `harvested_at` timestamp

Note: TTL estimates are heuristic. Actual session lifetime depends on platform activity, IP changes, and platform policy. A `HEALTHY` session may still fail `verify`.

### `monitor.py` — Bulk Status

`check_all(vault)` iterates all known platforms and returns a list of `SessionHealth` objects. Used by `status` and `doctor` CLI commands.

---

## Layer 2: Browser Layer

**Location:** `src/agentreach/browser/`

### `harvester.py` — Session Harvesting

Harvesting opens a **visible** (non-headless) Playwright browser. The user sees a real browser window and logs in normally. AgentReach detects post-login state by watching for a URL pattern match:

```python
await page.wait_for_url(f"**{post_login_pattern}**", timeout=timeout * 1000)
```

Once the URL matches (e.g. `kdp.amazon.com/title-setup` for KDP), the page's cookies are extracted and saved to the vault:

```python
cookies = await context.cookies()
vault.save(platform, {"cookies": cookies, "harvested_at": datetime.now(timezone.utc).isoformat()})
```

**No "type done" prompt exists.** The harvester auto-detects login completion via URL pattern.

Each platform defines its own `post_login_pattern`. If the platform changes its post-login URL structure, the harvester will time out and save whatever state currently exists.

Stealth mode is applied if `playwright-stealth` is installed:
```python
try:
    from playwright_stealth import stealth_async
    await stealth_async(page)
except ImportError:
    pass  # stealth optional
```

> ⚠️ `playwright-stealth` is not in the declared dependencies. Install manually: `pip install playwright-stealth`

### `session.py` — Headless Session Loading

Takes saved cookies and injects them into a new headless Playwright browser context:

```python
async def platform_context(platform: str, vault: SessionVault) -> BrowserContext:
    session = vault.load(platform)
    cookies = session["cookies"]
    context = await browser.new_context()
    await context.add_cookies(cookies)
    return context
```

Stealth mode is also applied to headless contexts to reduce bot detection signal.

### `uploader.py` — React Upload Bypass

File inputs inside React apps use controlled components — standard `input.setFiles()` is intercepted and often ignored. The uploader tries 4 strategies in order:

| Strategy | Method | Works For |
|---|---|---|
| 1 | Native input value setter override (React internals) | Most React forms |
| 2 | JavaScript File constructor + dispatchEvent | ⚠️ Currently broken — sends "placeholder" instead of file content |
| 3 | Playwright's `set_input_files()` with selector fallback | Non-React or hybrid forms |
| 4 | Drag-and-drop simulation | Drop zones |

Strategy 1 is the primary mechanism. If it fails, strategy 3 is the reliable fallback. Strategy 2 is broken (known bug) and strategy 4 has timing-dependent reliability.

---

## Layer 3: Platform Drivers

**Location:** `src/agentreach/drivers/`

### `base.py` — BasePlatformDriver

All drivers inherit from `BasePlatformDriver`:

```python
class BasePlatformDriver(ABC):
    platform_name: str = "unknown"

    def __init__(self, vault: Optional[SessionVault] = None):
        self.vault = vault or SessionVault()

    def require_valid_session(self) -> None:
        # Health check gate — exits cleanly if session missing/expired

    @abstractmethod
    async def verify_session(self) -> bool:
        # Live HTTP/browser check — returns True if authenticated
```

`require_valid_session()` is called at the top of every CLI command that needs a session. It exits with a human-readable message rather than a stack trace if the session isn't ready.

### Driver Registry

```python
# drivers/__init__.py
DRIVERS = {
    "kdp":       KDPDriver,
    "etsy":      EtsyDriver,
    "gumroad":   GumroadDriver,
    "pinterest": PinterestDriver,
    "reddit":    RedditDriver,
    "twitter":   TwitterDriver,
    "nextdoor":  NextdoorDriver,
}

def get_driver(platform: str) -> BasePlatformDriver:
    cls = DRIVERS[platform]  # KeyError if not found
    return cls()
```

TikTok is in `PLATFORM_META` for display purposes but is not in `DRIVERS`. Calling `get_driver("tiktok")` will raise `KeyError`.

### Driver Profiles

#### KDP (`kdp.py`)
- **Auth:** Browser session (cookies)
- **Mechanism:** Playwright automation of the KDP title-setup form
- **Known limitation:** KDP requires "step-up authentication" for upload operations. During harvest, the user must navigate to the actual title-setup form page (not just the dashboard) to capture the elevated-auth cookies. If this step is missed, uploads will fail with a step-up auth redirect. The driver detects this and returns a clear error.
- **Key methods:** `upload_paperback(details, manuscript_path, cover_path)`, `get_bookshelf()`, `resume_paperback(book_id)`

#### Etsy (`etsy.py`)
- **Auth:** API key + OAuth access token
- **Mechanism:** Etsy v3 REST API for listing creation; Playwright for image/digital file uploads (API doesn't support these directly)
- **Key methods:** `create_listing(listing)`, `publish_listing(listing)`

#### Gumroad (`gumroad.py`)
- **Auth:** API access token (stored in vault via `set-token`)
- **Mechanism:** Gumroad REST API for sales/products; browser automation for product creation
- **Note:** Product URL is dynamically extracted from the page after creation. Falls back to the seller's subdomain (fetched from Gumroad API during `verify_session()` and stored in vault) — never hardcoded.
- **Key methods:** `check_sales(after=None)`, `list_products()`, `publish_product(product)`

#### Pinterest (`pinterest.py`)
- **Auth:** Browser session (cookies)
- **Mechanism:** Playwright automation of Pinterest's pin creation UI
- **Key methods:** `post_pin(pin)`, `create_board(name, description)`

#### Reddit (`reddit.py`)
- **Auth:** Browser session (cookies)
- **Mechanism:** Playwright automation; uses clipboard paste strategy for Lexical rich-text editor
- **Key methods:** `post(subreddit, title, body)`, `comment(thread_url, text)`

#### Twitter (`twitter.py`)
- **Auth:** Browser session (cookies)
- **Mechanism:** Playwright automation of X's tweet compose UI
- **Key methods:** `tweet(text)`, `reply(tweet_url, text)`

#### Nextdoor (`nextdoor.py`)
- **Auth:** Browser session (cookies)
- **Mechanism:** Playwright automation of Nextdoor's post creation UI
- **Key methods:** `post(text)`

---

## CLI Architecture

`cli.py` uses Typer with sub-apps:

```python
app = typer.Typer()
kdp_app = typer.Typer()
etsy_app = typer.Typer()
# etc.

app.add_typer(kdp_app, name="kdp")
```

This produces commands like `agentreach kdp upload`, `agentreach etsy publish`, etc.

All platform commands follow the same pattern:
1. Build a dataclass payload from CLI arguments
2. Instantiate the driver
3. Call `driver.require_valid_session()` — exits cleanly if not ready
4. Call the action method (synchronous wrapper around `asyncio.run()`)
5. Print result with Rich

---

## Data Flow: Complete Upload Example

```
agentreach kdp upload --manuscript book.pdf --cover cover.pdf --title "My Book"
│
├── cli.py: builds KDPBookDetails dataclass
├── cli.py: KDPDriver() → __init__ → SessionVault()
├── cli.py: driver.require_valid_session()
│   └── vault.load("kdp") → health check → OK or sys.exit(1)
│
├── driver.upload_paperback(details, manuscript, cover)
│   └── asyncio.run(_upload_async(...))
│       ├── session.py: platform_context("kdp", vault)
│       │   └── loads cookies → new headless context → cookies injected
│       │
│       ├── page.goto("https://kdp.amazon.com/title-setup/new/paperback")
│       ├── _fill_step1_details(page, details)   # title, subtitle, author
│       ├── _fill_description_ckeditor(page, details.description)
│       ├── _navigate_to_content_tab(page)
│       ├── upload_file(page, manuscript_selector, manuscript_path)
│       │   └── uploader.py: try strategy 1 → 3 → 4
│       ├── upload_file(page, cover_selector, cover_path)
│       ├── _extract_book_id(page.url)
│       └── return UploadResult(success=True, product_id=book_id)
│
└── cli.py: print "✅ Uploaded. KDP ID: ..."
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `playwright` | ≥1.40.0 | Browser automation |
| `httpx` | ≥0.25.0 | Async HTTP for API drivers |
| `cryptography` | ≥41.0.0 | Fernet/AES-128-CBC + PBKDF2 |
| `typer` | ≥0.9.0 | CLI framework |
| `rich` | ≥13.0.0 | Terminal output |
| `playwright-stealth` | 2.0.2 | Bot detection evasion (not in declared deps — install separately) |

**Python requirement:** 3.10+ (uses union type syntax `str | Path`, lowercase generic types `list[str]`)

---

## Testing

```bash
pytest tests/                         # Run all tests
pytest tests/test_vault.py -v        # Vault tests only
```

Current coverage: vault only (4 tests). Driver tests require mocked Playwright contexts — see the test file for the pattern to follow.

---

## Known Issues

The critical bugs identified in the original audit have been fixed:

1. **Uploader strategy 2** ✅ — Now sends real base64-encoded file bytes injected as a proper `Blob` with the correct MIME type.
2. **Gumroad seller URL** ✅ — Dynamically extracted from page after creation; falls back to seller subdomain fetched from API during `verify_session()` and stored in vault.
3. **Vault path sanitization** ✅ — `_path()` rejects any traversal characters (`/`, `\`, `.`, null) outright with a clear `ValueError`.
4. **Etsy upload responses** ✅ — Every image and digital file upload response is checked; failures are collected and reported in the `UploadResult.message`.
5. **Vault load() swallows errors** ✅ — `VaultCorruptedError` is raised with a descriptive message distinguishing decryption failure from missing session.
6. **Encryption key hardening** ✅ — New installs use a cryptographically random 32-byte salt. Legacy installs derive the same MAC-based salt for backward compatibility, then persist it.

See [CHANGELOG.md](../CHANGELOG.md) for full fix history.

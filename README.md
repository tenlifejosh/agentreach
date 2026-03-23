# AgentReach

**Persistent authenticated web access for AI agents. Harvest a session once — automate forever.**

AgentReach gives AI agents the ability to act on web platforms (KDP, Etsy, Gumroad, Pinterest, Reddit, X, Nextdoor) without ever asking a human to open a browser again. You log in once. The session is encrypted locally. Every future operation runs headless.

[![PyPI version](https://img.shields.io/pypi/v/agentreach)](https://pypi.org/project/agentreach/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)

---

## Install

```bash
pip install agentreach
playwright install chromium
```

---

## 60-Second Quickstart

```bash
# 1. Harvest your first session (opens a browser — log in normally)
agentreach harvest kdp

# 2. Check everything's healthy
agentreach doctor

# 3. Do something real
agentreach kdp upload \
  --manuscript interior.pdf \
  --cover cover.pdf \
  --title "My Book" \
  --author "Jane Smith" \
  --price 12.99
```

That's it. No passwords stored. No API keys for KDP. Just your encrypted session, living on your local machine.

---

## How It Works

```
┌────────────────────────────────────────────────────────┐
│                        YOU                             │
│          agentreach harvest <platform>                  │
│          (opens a browser — log in once)               │
└──────────────────────────┬─────────────────────────────┘
                           │ cookies + tokens
                           ▼
┌────────────────────────────────────────────────────────┐
│                    Session Vault                        │
│        ~/.agentreach/vault/<platform>.vault            │
│        AES-256 encrypted, machine-specific key         │
└──────────────────────────┬─────────────────────────────┘
                           │ decrypted at runtime
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Platform Drivers                       │
│   ┌─────────┐ ┌──────┐ ┌─────────┐ ┌───────────────┐  │
│   │   KDP   │ │ Etsy │ │Gumroad  │ │Pinterest/Reddit│ │
│   │(browser)│ │(API) │ │(API+br) │ │Twitter/Nextdoor│ │
│   └─────────┘ └──────┘ └─────────┘ └───────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │ results
                           ▼
┌────────────────────────────────────────────────────────┐
│                    Your AI Agent                        │
│         UploadResult(success=True, product_id=...)     │
└────────────────────────────────────────────────────────┘
```

**Two auth models:**
- **Browser-based** (KDP, Pinterest, Reddit, X, Nextdoor): harvests cookies from a real login, replays them in headless Playwright
- **API-based** (Etsy, Gumroad): stores your OAuth token/API key in the encrypted vault

---

## Features

- **Encrypted session vault** — AES-256-CBC + HMAC (Fernet) with machine-specific key derivation via PBKDF2 (480,000 iterations). Nothing leaves disk.
- **Session health monitoring** — TTL-based expiry estimates, `status` command, `doctor` command with actionable recommendations
- **Browser session harvester** — opens a visible browser, waits for you to log in, captures cookies automatically via URL pattern detection
- **Headless session replay** — injects harvested cookies into a Playwright context and runs automation silently
- **React/SPA upload bypass** — 4-strategy engine to set file inputs in React-controlled forms (native property setter, drag-and-drop simulation, clipboard API)
- **Platform-specific drivers** — each driver understands the platform's forms, selectors, and quirks
- **CLI with Rich output** — color-coded status tables, actionable error messages, `doctor` for full diagnostics
- **Vault backup/restore** — encrypted export for disaster recovery (machine-bound by default)

---

## Platform Drivers

| Platform | Status | Auth Method | Actions |
|---|---|---|---|
| Amazon KDP | ✅ Stable | Browser session | Upload paperback, resume draft, list bookshelf |
| Etsy | ✅ Stable | API token + OAuth | Create listing, upload images, upload digital files |
| Gumroad | ✅ Stable | API token | Publish product, check sales, list products |
| Pinterest | ✅ Stable | Browser session | Create pin, create board |
| Reddit | ✅ Stable | Browser session | Post, comment |
| X / Twitter | ✅ Stable | Browser session | Tweet, reply |
| Nextdoor | ✅ Beta | Browser session | Post to neighborhood feed |
| TikTok | 🚧 Vault only | Browser session | Session storage only — no actions yet |

> **Browser-based drivers are inherently fragile.** Platform UI changes will break selectors. Selectors were last verified March 2026. Expect maintenance over time.

---

## CLI Reference

### Global commands

```bash
agentreach --version                  # Show version
agentreach status                     # Session health table (all platforms)
agentreach doctor                     # Full diagnostics: sessions + drivers + vault + Playwright
agentreach platforms                  # List all platforms with auth method and status
agentreach harvest <platform>         # Bootstrap a session (opens browser)
agentreach verify <platform>          # Verify a saved session with a live request
agentreach backup [--output path]     # Export encrypted vault bundle
agentreach restore <file.enc>         # Import vault bundle
agentreach restore <file.enc> --overwrite   # Overwrite existing sessions
```

### KDP

```bash
agentreach kdp upload \
  --manuscript interior.pdf \
  --cover cover.pdf \
  --title "My Book" \
  --subtitle "A Subtitle" \
  --author "Jane Smith" \
  --description "<p>Book description here.</p>" \
  --price 12.99 \
  --keywords "journal,planner,gift"

agentreach kdp bookshelf              # List books with status
```

### Etsy

```bash
# One-time credential setup
agentreach etsy set-credentials \
  --api-key YOUR_API_KEY \
  --access-token YOUR_TOKEN \
  --shop-id YOUR_SHOP_ID

# Publish a listing
agentreach etsy publish \
  --title "Printable Planner 2026" \
  --description "A beautiful digital planner..." \
  --price 4.99 \
  --digital-file planner.pdf \
  --images mock1.jpg,mock2.jpg \
  --tags "planner,printable,digital download"
```

### Gumroad

```bash
# One-time token setup
agentreach gumroad set-token YOUR_ACCESS_TOKEN

# Publish a product
agentreach gumroad publish \
  --name "My Digital Product" \
  --description "Product description..." \
  --price 7.99 \
  --file product.pdf \
  --url custom-url-slug

# Check sales
agentreach gumroad sales
agentreach gumroad sales --after 2026-01-01
```

### Pinterest

```bash
agentreach harvest pinterest          # One-time login

agentreach pinterest pin \
  --title "My Pin Title" \
  --description "Pin description..." \
  --image mockup.jpg \
  --link https://your-shop.com \
  --board "My Board Name"
```

### Reddit

```bash
agentreach harvest reddit             # One-time login

agentreach reddit post selftext "My Title" "Post body text"
agentreach reddit comment https://reddit.com/r/.../comments/... "Comment text"
```

### X / Twitter

```bash
agentreach harvest twitter            # One-time login

agentreach twitter tweet "Your tweet text here (max 280 chars)"
agentreach twitter reply https://x.com/user/status/123456 "Reply text"
```

### Nextdoor

```bash
agentreach harvest nextdoor           # One-time login

agentreach nextdoor post "Your neighborhood post text here"
```

---

## Security Model

Sessions are stored in `~/.agentreach/vault/` as individual `.vault` files — one per platform.

**Encryption:** Fernet (AES-256-CBC + HMAC-SHA256). The key is derived via PBKDF2-HMAC-SHA256 with 480,000 iterations using your machine's MAC address as the seed. This makes vault files non-portable by design — a vault file moved to another machine cannot be decrypted.

**What's stored:** Playwright cookies (serialized JSON), OAuth tokens, API keys, and metadata (`harvested_at`, `_saved_at`).

**What leaves disk:** Nothing. All encryption/decryption is local. AgentReach makes no network calls except to the target platform.

**Backup portability:** `agentreach backup` re-encrypts the bundle with the same machine-specific key. Backups can only be restored on the same machine.

**Known limitations:**
- MAC address-based key derivation means vault is unrecoverable if your network interface changes (VMs, hardware replacement)
- No protection against local root access — if an attacker has root on your machine, they can read the MAC and reconstruct the key
- `playwright-stealth` is used to reduce bot detection but is not guaranteed

See [docs/SECURITY.md](docs/SECURITY.md) for the full threat model.

---

## Contributing

1. Fork and clone
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -e ".[dev]"`
4. `playwright install chromium`
5. `pytest tests/` — make sure the 4 vault tests pass

**Adding a driver:** See [docs/DRIVERS.md](docs/DRIVERS.md) for the step-by-step guide and template.

**What needs work:**
- Tests — currently only vault is tested. Driver tests with mocked `platform_context` are the top priority.
- Error handling — most drivers swallow exceptions silently. They should log and surface errors.
- Uploader strategy 2 (`uploader.py`) sends placeholder content instead of real file bytes — needs fixing.
- Gumroad driver hardcodes a seller URL — needs to be extracted from the page post-creation.

Pull requests welcome. Open an issue first for anything bigger than a bug fix.

---

## Roadmap

**v0.3**
- Fix upload strategy 2 (binary file content via JS)
- Fix Gumroad hardcoded seller URL
- Add path traversal sanitization in vault `_path()`
- Add `playwright-stealth` to declared dependencies
- CLI tests via `typer.testing.CliRunner`
- Health check TTL for Reddit and Twitter

**v0.4**
- Full error logging (currently silent swallows everywhere)
- TikTok driver actions
- `--json` output flag on all commands

**v1.0**
- LinkedIn driver
- YouTube Studio driver
- Shopify driver
- Test coverage ≥ 60%
- Proper async error propagation throughout

---

## License

MIT © Joshua Noreen / Ten Life Creatives

See [LICENSE](LICENSE) for full terms. Commercial use is permitted under MIT. If you're building something commercial on top of AgentReach, consider contributing improvements back.

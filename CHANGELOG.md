# Changelog

All notable changes to AgentReach. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — 2026-03-23

### Added
- MCP server (`agentreach-mcp`) — 6 tools, 3 resources, 3 prompts for Claude Desktop, Cursor, and any MCP-compatible client
- Full test suite — unit tests for vault, CLI, browser, drivers, health monitoring, edge cases (100+ assertions)
- `docs/MCP_SETUP.md` — step-by-step MCP integration guide for Claude Desktop and Cursor
- `agentreach-mcp` CLI entrypoint registered in `pyproject.toml`

### Changed
- Security hardening: vault `_path()` now sanitizes input against path traversal
- `gumroad.py`: seller URL is now derived from the authenticated session, not hardcoded
- `browser/uploader.py`: strategy 2 fixed — sends real file content via multipart form
- TikTok removed from `PLATFORM_META` until a real driver exists (no more `KeyError`)
- `playwright-stealth` added to declared dependencies

### Fixed
- All critical bugs identified in codebase audit — see git history for details

---

## [0.2.1] — 2026-03-23

### Added
- `nextdoor.py` driver — post to Nextdoor neighborhood feed via browser session
- `agentreach nextdoor post` CLI command
- `agentreach twitter reply` CLI command — reply to a tweet by URL
- `agentreach reddit post` CLI command — create text posts in subreddits
- `agentreach verify <platform>` command — live session verification via HTTP
- `agentreach platforms` command — list all platforms with auth method and session status
- `agentreach backup` and `agentreach restore` commands — encrypted vault export/import
- `doctor` command — full system diagnostics: sessions, driver loading, vault path, Playwright availability
- Session health monitoring (`vault/health.py`, `vault/monitor.py`) — TTL-based expiry estimation
- `SessionStatus` enum: `HEALTHY`, `EXPIRING_SOON`, `EXPIRED`, `MISSING`, `UNKNOWN`
- `check_all()` — bulk health check across all known platforms
- Rich terminal output throughout: color-coded status tables, actionable error messages
- `UploadResult` dataclass standardizing driver return values
- `BasePlatformDriver.require_valid_session()` — clean exit with human-readable message on expired/missing session
- `browser/uploader.py` — 4-strategy React upload bypass engine

### Changed
- KDP driver: improved step-up auth detection with clear error messaging
- Etsy driver: moved to Etsy v3 REST API for listing creation
- Gumroad driver: added API-based sales reporting and product listing
- Pinterest driver: added board creation with fallback logic
- Reddit driver: clipboard paste strategy for Lexical editor (more reliable than character-by-character typing)

---

## [0.2.0] — 2026-02-01

### Added
- `etsy.py` driver — Etsy API integration for listing creation and image/file upload
- `gumroad.py` driver — Gumroad API for sales checking; browser fallback for product creation
- `pinterest.py` driver — pin and board creation via browser session
- `reddit.py` driver — comment and post via browser session
- `twitter.py` driver — tweet and reply via browser session
- `agentreach status` command — Rich table showing session health for all platforms
- Full Typer CLI with sub-apps per platform (`agentreach kdp`, `agentreach etsy`, etc.)
- `vault/store.py` — `SessionVault` class with AES-256 Fernet encryption
- PBKDF2-HMAC-SHA256 key derivation with 480,000 iterations
- Machine-specific key (MAC address seed) — vault non-portable by design
- `agentreach harvest <platform>` — visible-browser session capture with auto URL-pattern detection
- `agentreach --version` and `agentreach version` commands

### Changed
- KDP driver rewritten from scratch — handles all 3 upload steps, step-up auth detection, CKEditor description strategy

---

## [0.1.0] — 2026-01-10

### Added
- Initial release
- `kdp.py` driver — Amazon KDP paperback upload via browser automation
- `browser/harvester.py` — visible browser session harvesting
- `browser/session.py` — headless session loading via cookie injection
- Basic vault storage (unencrypted JSON — replaced in 0.2.0)
- `agentreach harvest kdp` — first working CLI command
- `agentreach kdp upload` — paperback upload to KDP
- `agentreach kdp bookshelf` — list KDP bookshelf
- `pyproject.toml` with Playwright, httpx, typer, rich as dependencies
- MIT license

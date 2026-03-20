# AgentReach Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.2.0] — 2026-03-20

### Added

- **`vault/monitor.py`** — Session expiry monitor. Categorizes all sessions as healthy/warning/critical/expired/missing. Prints clear alerts with exact re-harvest commands for anything needing attention.

- **`agentreach doctor`** — Full system health check command. Beautiful Rich output: sessions table, driver load status, vault path/stats, Playwright availability, and actionable recommendations.

- **`agentreach status`** (upgraded) — Now renders a Rich table with platform icon, name, colored status badge, days remaining, and last harvested timestamp. Summary line at bottom.

- **`agentreach backup`** — Export encrypted vault to `~/.agentreach/backups/vault-YYYY-MM-DD.enc`. Bundles all platform sessions into a single encrypted archive.

- **`agentreach restore`** — Import vault sessions from a backup `.enc` file. Skips existing sessions by default; use `--overwrite` to replace.

- **`agentreach platforms`** — List all supported platforms with current session status, auth method, and bootstrap command.

- **Smart session pre-checks in `BasePlatformDriver`** — `require_valid_session()` method. Before any operation, checks session health. If expired or missing: prints a friendly message with the exact re-harvest command and exits cleanly. No stack traces.

- All platform driver commands now call `require_valid_session()` before executing.

### Changed

- Version bumped from `0.1.0` → `0.2.0` in `pyproject.toml` and `__init__.py`.
- `agentreach --version` / `-v` now supported via callback.

### Dependencies

- `rich>=13.0.0` (already present in v0.1.0 — no new dependency needed)

---

## [0.1.0] — 2026-03-14

### Initial Release

- Session vault (AES-256 encrypted, machine-specific key)
- Browser harvester (Playwright, visible browser, human logs in once)
- Platform drivers: KDP, Etsy, Gumroad, Pinterest, Reddit, Twitter/X
- CLI: `harvest`, `verify`, `status`
- KDP step-up authentication support (deep auth cookie capture)

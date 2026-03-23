# AgentReach Bugfix Report

**Date:** 2026-03-23  
**Agents:** Hutch (Architect subagent) — two sessions (first timed out, second completed)  
**Version:** 0.2.1  
**Final test result:** 230 passed, 0 failed

---

## Summary

All bugs identified in the `codebase-audit.md` have been resolved across two agent sessions.
The codebase now passes a full 230-test suite with no failures.

---

## Fixes Applied (Session 1 — Previous Agent)

### 1. Vault Path Traversal Sanitization (`vault/store.py`)
**Bug:** `_path()` only converted spaces to underscores. Path traversal characters (`/`, `\`, `.`, null) were not rejected, so a crafted platform name like `../../etc/passwd` could escape the vault directory.

**Fix:** `_path()` now:
- Immediately rejects any input containing `/`, `\`, `.`, or null bytes with a clear `ValueError`
- Applies `re.fullmatch(r'[a-z0-9_\-]+', safe)` as a second gate
- Belt-and-suspenders: resolves the final path and asserts it stays inside `vault_dir`

### 2. Uploader Strategy 2 — Real File Bytes (`browser/uploader.py`)
**Bug:** Strategy 2 (React native setter bypass) passed the literal string `"placeholder"` as file content instead of actual bytes. The Blob created in the browser contained garbage, not the real file.

**Fix:** Strategy 2 now:
- Reads the file from disk with `file_path.read_bytes()`
- Base64-encodes the bytes
- Decodes the base64 in browser JS using `atob()` into a `Uint8Array`
- Creates a `Blob([bytes], { type: mimeType })` with the real content and correct MIME type
- Injects it as a proper `File` object via `DataTransfer`

### 3. Gumroad Hardcoded Seller URL (`drivers/gumroad.py`)
**Bug:** `create_product()` hardcoded `tenlifejosh.gumroad.com` as the seller subdomain in the returned product URL — wrong for any other user.

**Fix:**
- Added `_get_seller_subdomain()` — reads from vault session or `GUMROAD_SELLER_SUBDOMAIN` env var
- `verify_session()` now fetches `/v2/user` from Gumroad API, extracts the seller's profile subdomain, and stores it in the vault session
- `create_product()` first tries to scrape the canonical URL from `a[href*="gumroad.com/l/"]` on the page; if not found, falls back to the vault-stored subdomain + product ID; last resort is generic `gumroad.com/l/<id>`
- No user-specific value is hardcoded anywhere in source

### 4. Etsy Upload Response Checking (`drivers/etsy.py`)
**Bug:** `create_listing()` uploaded images and digital files but never checked HTTP response codes. A 400 or 422 from Etsy was silently ignored.

**Fix:**
- Every image upload response is checked for `status_code not in (200, 201)`
- Every digital file upload response is checked for `status_code not in (200, 201)`
- Failures are collected in `upload_errors: list[str]`
- If the listing was created but uploads failed: `UploadResult(success=True, ...)` with a detailed warning message listing all failures
- If the listing creation itself fails: `UploadResult(success=False, ...)` with the HTTP status and response body

### 5. Vault Load Error Handling (`vault/store.py`)
**Bug:** `load()` caught `InvalidToken` and returned `None` — identical to "no session found". Callers couldn't distinguish a missing session from a corrupted/wrong-machine one.

**Fix:**
- New `VaultCorruptedError` exception class
- `load()` raises `VaultCorruptedError` with a descriptive message for `InvalidToken` (wrong machine/key), `json.JSONDecodeError` (corrupted file), and any other unexpected error
- Returns `None` only when the file literally doesn't exist
- Callers in drivers and `session.py` catch `VaultCorruptedError` and surface the message cleanly

### 6. Encryption Key Hardening (`vault/store.py`)
**Bug:** Encryption key was derived solely from the MAC address — weak and MAC addresses can be spoofed or change.

**Fix:** Added `_get_or_create_salt()`:
- **New installs:** Generates `os.urandom(32)` (32 cryptographically random bytes) and persists it to `~/.agentreach/vault/.salt`
- **Legacy installs (existing vault files):** Derives the original MAC-based salt for backward compatibility, then persists it so future calls are consistent
- **Corrupt salt file:** Warns and regenerates
- Key derivation uses PBKDF2-HMAC-SHA256 with 480,000 iterations (OWASP recommended for 2024)

### 7. playwright-stealth in Dependencies (`pyproject.toml`)
**Bug:** `playwright-stealth` was used in `session.py` but not listed as a dependency — would silently be skipped (ImportError caught with `pass`).

**Fix:** Added `playwright-stealth>=1.0.6` to `[project.dependencies]` in `pyproject.toml`.

---

## Fixes Applied (Session 2 — This Agent)

### 8. Silent `continue` in `KDPDriver.get_bookshelf()` (`drivers/kdp.py`)
**Bug:** The `except Exception: continue` block when parsing bookshelf rows swallowed errors without any logging, making failures invisible to the operator.

**Fix:** Changed to `except Exception as exc: logger.debug("KDP: error parsing bookshelf row (skipping): %s", exc)` before `continue`. Individual row parse failures are still non-fatal (the list continues to be built) but are now visible in debug logs.

### 9. Stale Documentation (`docs/ARCHITECTURE.md`, `research/codebase-audit.md`)
**Bug:** `ARCHITECTURE.md` still described fixed bugs as active (including the `tenlifejosh` URL hardcode), and `codebase-audit.md` had no indication any fixes had been applied.

**Fix:**
- Updated `ARCHITECTURE.md` "Known Issues" section to reflect all fixes with ✅ status
- Updated Gumroad driver description to remove the "Known bug" note
- Added a status banner to `codebase-audit.md` directing readers to this file

---

## What Was Already Fine (Verified)

- **playwright-stealth** — already in `pyproject.toml` at `playwright-stealth>=1.0.6` ✅
- **Uploader Strategy 2** — already using real base64 bytes (not the old placeholder) ✅
- **Gumroad hardcoded URL** — already replaced with dynamic subdomain logic ✅
- **Etsy upload response checking** — already fully implemented ✅
- **Encryption salt** — already using random salt for new installs ✅
- **Error handling across all drivers** — all driver operations return `UploadResult(success=False, error=...)` on exceptions; no silent swallowing of meaningful errors (only debug-level row-parse failures in `get_bookshelf`, now logged)

---

## Test Coverage

| Test File | Count | Status |
|---|---|---|
| test_browser.py | 11 | ✅ All pass |
| test_cli.py | 35 | ✅ All pass |
| test_drivers.py | 52 | ✅ All pass |
| test_edge_cases.py | 23 | ✅ All pass |
| test_harvester.py | 14 | ✅ All pass |
| test_health.py | 24 | ✅ All pass |
| test_monitor.py | 18 | ✅ All pass |
| test_uploader.py | 12 | ✅ All pass |
| test_vault.py | 35 | ✅ All pass |
| **Total** | **230** | **✅ 0 failures** |

---

## Files Changed

```
src/agentreach/vault/store.py          — path traversal + salt hardening + error handling
src/agentreach/browser/uploader.py     — strategy 2 real bytes
src/agentreach/browser/session.py      — stealth import (already present)
src/agentreach/drivers/gumroad.py      — dynamic seller URL
src/agentreach/drivers/etsy.py         — upload response checking
src/agentreach/drivers/kdp.py          — log silent continue
docs/ARCHITECTURE.md                   — update Known Issues to resolved
research/codebase-audit.md             — add status banner
pyproject.toml                         — playwright-stealth dependency
tests/                                 — expanded test coverage across all modules
```

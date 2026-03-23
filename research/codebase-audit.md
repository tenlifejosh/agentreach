# AgentReach Codebase Audit
**Date:** 2026-03-23  
**Auditor:** Hutch (Architect subagent)  
**Version audited:** 0.2.1  
**Scope:** Full source audit — quality, bugs, security, coverage, docs, dependencies

> **⚠️ STATUS NOTE (2026-03-23):** The bugs identified in this audit (BUG-001 through BUG-009) have been fixed in subsequent commits. This document is preserved as a historical record. See `research/bugfix-report.md` for the complete fix summary and `CHANGELOG.md` for version history.

---

## 1. File & Module Inventory

### Project Structure

```
agentreach/
├── src/agentreach/
│   ├── __init__.py            # Package version (0.2.1)
│   ├── cli.py                 # Full Typer CLI — all commands
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── store.py           # SessionVault — AES-256 encrypted storage
│   │   ├── health.py          # SessionHealth — expiry detection
│   │   └── monitor.py        # Session categorization + alerts
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── harvester.py       # Cookie harvest via visible browser
│   │   ├── session.py         # Load sessions into headless context
│   │   └── uploader.py        # React-bypass file upload engine
│   └── drivers/
│       ├── __init__.py        # Registry + get_driver()
│       ├── base.py            # BasePlatformDriver ABC
│       ├── kdp.py             # Amazon KDP (browser automation)
│       ├── etsy.py            # Etsy (API + browser fallback)
│       ├── gumroad.py         # Gumroad (API + browser fallback)
│       ├── pinterest.py       # Pinterest (browser automation)
│       ├── reddit.py          # Reddit (browser automation)
│       ├── twitter.py         # X/Twitter (browser automation)
│       └── nextdoor.py        # Nextdoor (browser automation)
├── tests/
│   └── test_vault.py          # 4 basic vault tests (all pass)
├── skills/agentreach/
│   └── SKILL.md               # OpenClaw integration docs
├── docs/
│   └── GETTING-STARTED.md
├── README.md
├── CHANGELOG.md
├── COMMERCIAL.md
└── pyproject.toml
```

### Feature Inventory

| Feature | Status |
|---|---|
| Encrypted vault (AES-256) | ✅ Implemented |
| Session health checks | ✅ Implemented |
| Session expiry monitoring | ✅ Implemented |
| Cookie harvesting (visible browser) | ✅ Implemented |
| Headless session loading | ✅ Implemented |
| React upload bypass (4 strategies) | ✅ Implemented |
| KDP driver — upload paperback | ✅ Implemented |
| KDP driver — resume draft | ✅ Implemented |
| KDP driver — bookshelf listing | ✅ Implemented |
| Etsy driver — API listing creation | ✅ Implemented |
| Etsy driver — image upload | ✅ Implemented |
| Etsy driver — digital file upload | ✅ Implemented |
| Gumroad driver — API sales check | ✅ Implemented |
| Gumroad driver — browser product creation | ✅ Implemented |
| Pinterest driver — pin creation | ✅ Implemented |
| Pinterest driver — board creation | ✅ Implemented |
| Reddit driver — comment | ✅ Implemented |
| Reddit driver — post | ✅ Implemented |
| Twitter driver — tweet | ✅ Implemented |
| Twitter driver — reply | ✅ Implemented |
| Nextdoor driver — neighborhood post | ✅ Implemented |
| CLI: harvest, verify, status, doctor | ✅ Implemented |
| CLI: backup, restore, platforms | ✅ Implemented |
| CLI: all platform subcommands | ✅ Implemented |
| TikTok driver | ❌ Session vault only, no actions |
| LinkedIn driver | ❌ Not implemented |
| Shopify driver | ❌ Not implemented |
| YouTube Studio driver | ❌ Not implemented |
| API server (FastAPI) | ❌ Referenced in README architecture, not in codebase |

---

## 2. Bugs, TODOs, Hacks, and Known Issues

### Confirmed Bugs

#### BUG-001: `harvest()` instruction says "type `done`" but doesn't implement it
**File:** `browser/harvester.py`  
**Severity:** HIGH — documentation vs. implementation mismatch

The `GETTING-STARTED.md` docs say: *"Once you're logged in and on the dashboard, type `done` in the terminal"*. The actual harvester **never prompts for `done`** — it auto-detects post-login URL patterns via `wait_for_url()`. If the URL pattern fails to match (wrong URL, platform updated their routing), the harvester silently times out and captures whatever state exists. No user feedback. No "type done" prompt. The docs are wrong.

```python
# harvester.py — no terminal prompt, just URL pattern matching
await page.wait_for_url(f"**{post_login_pattern}**", timeout=timeout * 1000)
```

#### BUG-002: `uploader.py` Strategy 2 sends file content as literal string `"placeholder"`
**File:** `browser/uploader.py`  
**Severity:** HIGH — Strategy 2 is broken by design

```python
result = await page.evaluate("""...create file from content...""",
    [input_selector, file_path.name, "placeholder"],  # ← literal "placeholder"
)
```

The `evaluate()` call passes `"placeholder"` instead of the actual file content. The Blob created in the browser contains only the string "placeholder", not the actual file bytes. This strategy would set a malformed file on the input. It's the second-most-important fallback, and it's broken.

**Note:** Strategy 2 is actually doing the wrong thing anyway — reading binary file content into a JS string doesn't work for binary files. This needs a fundamentally different approach (e.g., base64 encoding).

#### BUG-003: `gumroad.py` hardcodes the seller URL to `tenlifejosh`
**File:** `drivers/gumroad.py`  
**Severity:** MEDIUM — multi-user product killer

```python
gumroad_url = f"https://tenlifejosh.gumroad.com/l/{product.custom_url or product_id}"
```

This is hardcoded to Joshua's Gumroad account. If anyone else installs AgentReach and uses the Gumroad driver, the returned URL will point to the wrong account. The actual URL should be extracted from the page after creation.

#### BUG-004: KDP `_fill_description_ckeditor` uses f-string `repr()` for arbitrary HTML
**File:** `drivers/kdp.py`  
**Severity:** MEDIUM — injection potential + fragility

```python
await page.evaluate(f"""
    nativeInputValueSetter.set.call(input, {escaped});
""")
```

While `json.dumps(html)` is used in Strategy 1 and is correct, Strategy 2 uses:
```python
nativeSetter.set.call(input, {escaped});
```
...where `escaped` is the `json.dumps()` output injected directly into a JavaScript string. This is generally fine with `json.dumps` but the pattern is fragile — if the HTML description contains certain edge cases (nested quotes, Unicode issues), the `evaluate()` can fail silently (the `except` catches everything and returns `False`).

#### BUG-005: `vault/store.py` `load()` silently returns `None` on decryption failure
**File:** `vault/store.py`  
**Severity:** MEDIUM — data loss is invisible

```python
except Exception:
    return None
```

If the vault file exists but fails to decrypt (corrupted file, key mismatch, truncated write), it silently returns `None`. This looks the same as "no session found". The caller (`require_valid_session()`) then shows "No session found — run harvest" instead of "Your vault file is corrupted — you may need to re-harvest."

#### BUG-006: `cli.py` references `api/server.py` that doesn't exist
**File:** `README.md`, `cli.py`  
**Severity:** LOW — architecture diagram only

The README shows `api/server.py` in the architecture diagram. No such file exists. The `cli.py` doesn't import it, so no runtime error — but it's a lie in the docs.

#### BUG-007: `pyproject.toml` declares Python 3.9+ but code uses Python 3.10+ features
**File:** `pyproject.toml`  
**Severity:** LOW — incorrect metadata

```toml
# README.md says:
![Python](https://img.shields.io/badge/python-3.9+-blue)

# pyproject.toml says:
requires-python = ">=3.10"

# Code uses 3.10+ syntax:
list[str]  # 3.10+ lowercase generics
str | Path  # 3.10+ union types
```

The README badge says Python 3.9+. `pyproject.toml` correctly says 3.10+. But the code uses 3.10+ union type syntax (`str | Path`, `dict[str, list]`). Consistent — but the README badge is wrong.

#### BUG-008: TikTok listed in `PLATFORM_META` with no driver, no warning
**File:** `cli.py`  
**Severity:** LOW — misleading UX

`PLATFORM_META` includes TikTok:
```python
"tiktok": {"icon": "🎵", "label": "TikTok"},
```

TikTok appears in `agentreach platforms` output with "No session" status but no indication that the driver doesn't exist. `get_driver("tiktok")` would `KeyError` because `DRIVERS` dict doesn't include it. The `doctor` command would crash on `get_driver("tiktok")` if it iterated `PLATFORM_META`.

Wait — `doctor` only calls `get_driver()` on `driver_names = ["kdp", "etsy", "gumroad", "pinterest", "reddit", "twitter"]` — so it avoids the crash by hardcoding the list to exclude TikTok. That's a smell.

#### BUG-009: `harvester.py` has orphaned comment `# TikTok added` mid-file
**File:** `browser/harvester.py`  
**Severity:** LOW — code hygiene

The string `# TikTok added` appears as a dangling comment between two file-level docstrings. Looks like `session.py`'s docstring was accidentally appended to `harvester.py`.

Actually — the file appears to contain TWO modules concatenated: `harvester.py` ends normally, then `session.py`'s module docstring begins immediately. This suggests a copy-paste accident during development. The file is actually just `harvester.py` + the beginning of `session.py` text. But since both files exist separately, this is just a comment artifact.

#### BUG-010: `etsy.py` doesn't check HTTP errors for image/file uploads
**File:** `drivers/etsy.py`  
**Severity:** MEDIUM — silent failures

```python
img_resp = await client.post(...)
await asyncio.sleep(0.5)
# ← img_resp is never checked
```

Upload responses for images and digital files are never checked. If an image upload fails (403, 422, timeout), the listing is still returned as `success=True`. The user has no idea their listing is live but has no images.

---

## 3. Code Quality Assessment

### What's Solid ✅

**Vault architecture** (`vault/store.py`): Clean, well-designed. PBKDF2 key derivation with 480,000 iterations. Machine-specific UUID as seed. Fernet (AES-256-CBC + HMAC) for authenticated encryption. The vault is genuinely secure for a local tool.

**Base driver pattern** (`drivers/base.py`): Excellent ABC design. `require_valid_session()` is the right place for health checks. Clean separation of concerns. New drivers are easy to add.

**Upload bypass engine** (`browser/uploader.py`): The *concept* is excellent — four strategies in order of reliability. Strategy 1 and 3 are solid. Strategy 4 (drag-and-drop) is a reasonable attempt. Only Strategy 2 is broken.

**Health check system** (`vault/health.py`, `vault/monitor.py`): Well-designed. TTL-based expiry estimation, clear severity bucketing. The `check_all()` + `monitor()` pattern is clean.

**CLI design** (`cli.py`): The `doctor` command is genuinely impressive for a v0.2 tool. Rich tables, color-coded output, actionable recommendations. This is pro-level UX.

**KDP driver** (`drivers/kdp.py`): The most complex driver. Well-documented with verified selectors and dates. Step-up auth problem is honestly explained. `resume_paperback()` for draft continuation is a thoughtful feature.

**Pinterest driver** (`drivers/pinterest.py`): Board creation fallback when board doesn't exist is a great touch. Verified selectors in the docstring.

**Reddit driver** (`drivers/reddit.py`): Clipboard paste strategy for Lexical editor + chunked typing fallback = solid resilience against the React editor problem.

### What's Fragile ⚠️

**All browser drivers**: Fundamentally fragile by nature — selectors are hardcoded and will break when platforms update their UI. There's no selector versioning, no update mechanism, no fallback testing. Each driver is a time bomb that will need maintenance every few months.

**KDP driver** — The step-up auth problem is documented but the "fix" requires the user to take manual steps during harvest. If they forget to navigate to the title-setup form, the session won't work for uploads. This is a workflow landmine.

**Gumroad browser driver** — The `create_product()` uses `networkidle` which can time out on slow connections. The dashboard/new product URL structure (`gumroad.com/products/new`) has changed before. And the hardcoded `tenlifejosh` URL is user-hostile.

**Selector brittleness across all drivers**: 
- Twitter: `[data-testid="tweetTextarea_0"]` — these data-testids change frequently
- KDP: `#data-print-book-title` — stable KDP IDs, actually reasonably solid
- Pinterest: `#storyboard-upload-input` — likely stable; Pinterest is slower to change
- Nextdoor: using class-based selectors + has-text which are the least stable

**`check_all()` in health.py** — Only knows about platforms in `PLATFORM_TTL_DAYS`. Reddit and Twitter have no TTL defined, so they fall back to `DEFAULT_TTL_DAYS = 30`. These platforms actually have different session lifetimes (Reddit ~90 days, Twitter is unpredictable). The TTL estimates are guesses.

**Exception handling is too broad everywhere**: Nearly every `try/except` catches bare `Exception` and either silently continues or returns `False`. This makes debugging extremely difficult. Errors disappear without any logging.

---

## 4. Missing Error Handling, Edge Cases, Security Issues

### Error Handling Gaps

| Location | Issue |
|---|---|
| `vault/store.py:load()` | Swallows all decryption errors with `except Exception: return None` |
| `browser/session.py:platform_context()` | Browser launch failures not distinguished from session failures |
| `browser/uploader.py` | Strategy failures are all silently swallowed |
| `drivers/etsy.py:create_listing()` | Image/file upload responses never checked |
| `drivers/gumroad.py:get_sales()` | `resp.raise_for_status()` but no handling for HTTP errors beyond status codes |
| `drivers/kdp.py:_fill_step1_details()` | Category fill completely swallowed: `except Exception as e: pass` |
| `cli.py:backup()` | References `_FERNET` directly — couples CLI to vault internals |
| `cli.py:gumroad_sales()` | `data.get("sales", [])` — never handles API errors |
| All drivers | No timeout on `asyncio.run()` calls — can hang indefinitely |

### Edge Cases

| Location | Edge Case |
|---|---|
| `vault/store.py:_derive_key()` | `uuid.getnode()` returns the MAC address. If the machine has no network interface, it returns a random number — different each run. Vault becomes permanently unreadable. |
| `vault/store.py:_derive_key()` | On VMs, MAC address changes on each provisioning, breaking vault portability. |
| `browser/harvester.py` | No handling for "browser already open" race condition if two harvests run simultaneously |
| `harvester.py:harvest_session()` | If vault.save() fails mid-write, partial data is silently lost |
| `drivers/etsy.py:create_listing()` | Tags list is sliced to `[:13]` but no error if user passes more — silent truncation |
| `drivers/kdp.py:create_paperback()` | `book_id = parts[1].split("/")[0]` — will IndexError if URL doesn't match pattern |
| `drivers/kdp.py:_fill_step1_details()` | Author name split assumes "First Last" — fails for single-name authors, names with multiple spaces |
| `cli.py:kdp_upload()` | Keywords parsed with `split(",")` — no stripping of whitespace around commas |

Wait — actually keywords do get stripped: `[k.strip() for k in keywords.split(",") if k.strip()]`. That one is fine. But images in `etsy_publish` use the same pattern and it does handle stripping.

### Security Issues

**SEC-001: Machine UUID as encryption seed is weak**
```python
machine_id = str(uuid.getnode()).encode()  # MAC address as int
```
MAC addresses are predictable and often known. An attacker who has the vault file and knows the machine's MAC address can reconstruct the encryption key via PBKDF2 with the same parameters. The PBKDF2 `salt` is derived from the machine_id itself: `salt = hashlib.sha256(machine_id).digest()` — so salt provides no additional entropy when machine_id is guessable.

**Mitigation path:** Add a random salt file stored alongside the vault, separate from the key derivation.

**SEC-002: `backup` command exports re-encrypted bundle using the same `_FERNET` key**
```python
encrypted = _FERNET.encrypt(payload)
output.write_bytes(encrypted)
```
The backup file is encrypted with the same machine-specific key. Copying the backup to another machine + running `restore` will fail because the key won't match. This is by design (non-portability) but makes backups nearly useless for disaster recovery. The docs don't explain this limitation.

**SEC-003: Access token stored in plaintext within vault JSON**
```python
existing["access_token"] = token
self.vault.save("gumroad", existing)
```
The vault *does* encrypt the whole JSON — so the token is encrypted at rest. But the token is loaded into memory as plaintext during any operation, and Python's GC doesn't guarantee immediate memory clearing. For a local tool at this stage, this is acceptable. At scale (cloud sync, team vaults), this needs proper secret handling.

**SEC-004: No validation of `platform` argument before filesystem operations**
```python
def _path(self, platform: str) -> Path:
    safe = platform.lower().replace(" ", "_")
    return self.vault_dir / f"{safe}.vault"
```
No path traversal prevention. `platform = "../../etc/passwd"` would create `passwd.vault` in `/etc/`. The `.replace(" ", "_")` only sanitizes spaces. A proper fix would be `re.sub(r'[^a-z0-9_-]', '', platform.lower())`.

**SEC-005: Playwright `--no-sandbox` flag in harvester**
```python
args=["--no-sandbox", "--start-maximized"],
```
`--no-sandbox` disables Chromium's sandbox isolation. Required in some CI environments but not needed for local use. If the harvested site serves malicious JS, the sandbox would normally contain it — this flag removes that protection. Should be removed for local desktop use.

**SEC-006: Stealth library silently skipped if not installed**
```python
try:
    from playwright_stealth import stealth_async
    await stealth_async(page)
except ImportError:
    pass  # stealth optional
```
`playwright-stealth` is not in `pyproject.toml` dependencies. Users who install from `pip install agentreach` won't get stealth. The detection bypass that makes browser sessions work is silently absent. Should be in `dependencies`, not optional.

---

## 5. Test Coverage

### Current State: Catastrophically Thin

**4 tests total.** All in `tests/test_vault.py`. All test the vault in isolation.

| Test | What it tests |
|---|---|
| `test_vault_init` | Vault object constructs without error |
| `test_vault_save_load` | Save + load round-trip works |
| `test_vault_delete` | Delete removes file |
| `test_vault_list_platforms` | List returns correct platform names |

**Zero tests for:**
- Any driver (KDP, Etsy, Gumroad, Pinterest, Reddit, Twitter, Nextdoor)
- CLI commands
- Browser harvester
- Session loading (`session.py`)
- Upload bypass (`uploader.py`)
- Health checker (`health.py`)
- Monitor (`monitor.py`)
- Backup/restore
- Error conditions

**Coverage estimate: <5% of codebase is tested.**

### What's Needed (Priority Order)

1. **Health checker unit tests** — test each `SessionStatus` scenario (mock vault data)
2. **Driver unit tests with mocked `platform_context`** — verify correct form fills, upload calls
3. **CLI integration tests using `typer.testing.CliRunner`** — verify all commands exit cleanly
4. **Vault error case tests** — corrupted file, wrong key, missing file
5. **Upload bypass tests** — mock page, verify strategy fallback chain
6. **E2E tests (optional)** — would require live credentials, skip in CI

The `pytest-asyncio` and `pytest-playwright` deps are installed but completely unused. The infrastructure exists to write async driver tests — just hasn't been done.

---

## 6. Documentation Quality

### README.md

**Strengths:**
- Clear problem statement and positioning
- Good comparison table vs alternatives
- Architecture diagram
- Real-world use cases

**Weaknesses:**
- Python badge says 3.9+, code requires 3.10+
- `pip install agentreach` — not on PyPI yet, so this will fail for anyone following the README
- `api/server.py` shown in architecture doesn't exist
- `agentreach harvest --platform kdp` syntax shown in README doesn't match CLI (correct syntax is `agentreach harvest kdp`)
- Several Quick Start examples use non-existent flags (`--product-dir`, `--listing-file` for `etsy publish`)

### GETTING-STARTED.md

**Weaknesses:**
- "type `done` in the terminal" — this doesn't happen (see BUG-001)
- `agentreach gumroad sales --days 7` — `--days` flag doesn't exist (it's `--after`)
- `print(f"Last 7 days: ${sales_data['total_revenue']:.2f}")` — `check_sales()` returns Gumroad's raw API response which doesn't have `total_revenue` key

### SKILL.md

Reasonably accurate for KDP, Gumroad, Etsy. Missing Reddit, Twitter, Nextdoor (these drivers exist and work but aren't documented in the skill).

### Inline Documentation

**Good:** `kdp.py` has excellent inline comments — verified selector IDs with dates, KDP step-up auth explanation, strategy comments in `_fill_description_ckeditor`. This is the standard other drivers should match.

**Missing:** Most other drivers have function docstrings but no inline comments on the "why" of selector choices. No dates for when selectors were last verified.

### CLI Help

The Typer CLI help is auto-generated and accurate. `agentreach --help`, `agentreach kdp --help` all work correctly. Help text is concise and useful.

---

## 7. Dependency Audit

### Runtime Dependencies

| Package | Installed | Minimum Required | Notes |
|---|---|---|---|
| playwright | 1.58.0 | >=1.40.0 | ✅ Current. Up to date. |
| httpx | 0.28.1 | >=0.25.0 | ✅ Current. |
| cryptography | 43.0.3 | >=41.0.0 | ⚠️ Latest is 44.x. 43.x has no known CVEs but is behind. |
| typer | 0.24.1 | >=0.9.0 | ✅ Current. |
| rich | 14.3.3 | >=13.0.0 | ✅ Current. |

### Missing from `pyproject.toml`

| Package | Installed | Issue |
|---|---|---|
| `playwright-stealth` | 2.0.2 | Used in `session.py` — not in dependencies. Silent failure if not installed. |
| `requests` | 2.32.5 | Installed but **not used anywhere in the codebase**. Orphaned dependency. |
| `pycookiecheat` | 0.8.0 | Installed but **not used**. Dead dependency. |
| `python-slugify` | 8.0.4 | Installed but **not used**. Dead dependency. |

### Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-playwright>=0.4",
]
```

Installed versions: pytest 9.0.2, pytest-asyncio 1.3.0, pytest-playwright 0.7.2 — all current.

**Note:** `pytest-asyncio 1.3.0` is a major version jump from the `>=0.21` requirement. The API changed significantly. `asyncio_mode = "auto"` in `pyproject.toml` handles the configuration difference, but any existing test patterns may need updating.

### Vulnerability Assessment

No known CVEs in the installed dependency set as of this audit date. The `cryptography 43.0.3` is slightly behind (44.x is current) but has no unpatched vulnerabilities.

**Highest risk surface:** `playwright-stealth 2.0.2` — this is a community package with no formal security review. It injects JavaScript into pages. Using it in an authenticated browser context means if the package is compromised (supply chain attack), it could exfiltrate session cookies. Low probability, high impact.

---

## 8. What Works Perfectly vs. What's Held Together with Tape

### Works Perfectly ✅

**Session vault**  
The encryption, storage, and retrieval work correctly. Tests pass. The design is solid. This is the most trustworthy part of the codebase.

**Session health system**  
`check_all()`, `check_session()`, and `monitor()` work correctly. The Rich output in `status` and `doctor` is polished and accurate.

**CLI UX**  
The `doctor` command especially is excellent. All commands have proper help text. Error messages are human-friendly. The backup/restore commands work.

**Etsy API integration**  
Using the official API with proper OAuth headers. `create_listing()` follows the correct Etsy v3 API flow. This is the most production-ready driver.

**Gumroad API integration**  
`verify_session()`, `list_products()`, `get_sales()` all use the official API correctly. `check_sales()` and `list_products()` should be reliable.

**KDP selector IDs**  
The KDP form selectors (`#data-print-book-title`, etc.) were verified against the live form. These are stable KDP element IDs — likely to survive UI updates.

**Reddit/Twitter text posting**  
The clipboard-paste strategy + chunked-typing fallback for Lexical/rich-text editors is a smart solution to a hard problem. The Reddit driver is the most thoughtfully implemented browser driver.

### Held Together with Tape ⚠️

**KDP step-up auth**  
The entire KDP upload workflow has a known critical limitation: step-up auth breaks the session for headless operation. The "fix" is documented but requires specific human behavior during harvest. It's fragile by design. The code detects the failure and returns a clear error message — that's good — but the underlying problem is unsolved.

**Gumroad browser product creation**  
The `create_product()` browser path uses `networkidle` (unreliable), dynamic product name input selectors, contenteditable description editing, and a hardcoded seller URL. Multiple brittleness vectors.

**Strategy 2 of uploader.py**  
Sends `"placeholder"` as file content. Technically broken. It probably never succeeds for real files, meaning the system is relying on Strategy 1 and 3 more than designed.

**Pinterest board creation flow**  
Multiple `wait_for` calls without guaranteed state. Board creation modal behavior varies based on account state. The re-open-dropdown-after-creation logic is a hack that may or may not work depending on timing.

**Twitter posting**  
Works when it works, but X actively detects automation. No rate limiting, no retry logic, no handling for "suspicious activity" redirects. One aggressive session and the account could be restricted.

**Nextdoor posting**  
The most uncertain driver. Nextdoor's DOM is the least documented, selectors are generic class-based, and the "fallback to news feed + click create post" path has many failure points.

**Session TTL estimates**  
The `PLATFORM_TTL_DAYS` for Reddit and Twitter aren't in the dict — they fall through to `DEFAULT_TTL_DAYS = 30`. Reddit sessions actually last ~90 days. Twitter is unpredictable. The health warnings will be wrong for these platforms.

---

## 9. Priority Fix List

### Critical (Fix Before Marketing)

1. **Fix BUG-002** (uploader.py Strategy 2 sends "placeholder") — core upload engine
2. **Fix SEC-004** (path traversal in vault _path()) — security hole
3. **Fix BUG-003** (hardcoded tenlifejosh Gumroad URL) — user-hostile for anyone not named Joshua
4. **Add `playwright-stealth` to pyproject.toml dependencies** — silent missing dependency
5. **Fix BUG-010: etsy image/file upload response never checked** — silent failures on listings

### High Priority (Fix Before Public Launch)

6. **Fix BUG-005** (vault load() swallows decryption errors) — add specific exception handling and a clear "vault corrupted" error
7. **Fix SEC-001** (weak encryption key derivation) — add a random salt file
8. **Fix docs: `--platform` flag in README doesn't match CLI** — first-run experience
9. **Fix docs: `type done`** instruction in GETTING-STARTED.md — not real
10. **Add TTL for Reddit and Twitter** to `PLATFORM_TTL_DAYS`
11. **Remove `--no-sandbox`** from harvester for local use
12. **Remove orphaned deps** (`requests`, `pycookiecheat`, `python-slugify`) from venv
13. **Remove hardcoded `author: str = "Joshua Noreen"`** from `KDPBookDetails` — should be empty default or loaded from config

### Medium Priority (Before v1.0)

14. **Add tests for health.py** — at minimum unit test all SessionStatus paths
15. **Add tests for CLI** using typer's CliRunner
16. **Add logging throughout** (currently all errors are swallowed silently)
17. **Add TikTok driver** or remove it from PLATFORM_META until implemented
18. **Document verified-selector dates** in all drivers (KDP has this, others don't)
19. **Fix KDP author name parsing** for edge cases (single name, suffixes)
20. **Update CHANGELOG format** — currently inconsistent structure
21. **Fix cryptography version** to >=44.0 for latest patches

### Nice to Have (Polish)

22. **Add `--json` output flag to CLI** for machine-readable status
23. **Add retry logic** to browser operations (currently single-attempt)
24. **Add configurable timeout** to all headless operations
25. **Implement TikTok driver** (just needs browser post action)
26. **Add `agentreach logs`** command for session activity history
27. **Create `api/server.py`** that's referenced in README architecture

---

## Summary

AgentReach is a genuinely clever product solving a real problem. The core architecture — vault, health system, harvester, headless session loading — is solid and well-designed. The KDP selector work shows real hands-on debugging. The CLI UX is ahead of what you'd expect from a v0.2 tool.

The weaknesses are exactly what you'd expect from rapid solo development: thin tests, some docs that describe aspirational behavior instead of actual behavior, a broken upload strategy that never got caught because Strategy 1 usually works, and some J-specific hardcoding that needs to come out before this touches other users' accounts.

The biggest actual risk is the Gumroad hardcoded URL and the broken uploader Strategy 2 — both of which are invisible failures that would damage trust immediately. Fix those first.

The security model is appropriate for a local tool. It would need a full rethink before cloud sync or team vaults (the Pro tier) — but that's fine, that's a v1.0 problem.

**Readiness assessment:**
- Personal use by one person who knows the limitations: ✅ Ready now
- Open source release with contributors: ⚠️ Fix the critical items first (~2-4 hours of work)
- Millions of users / commercial product: ❌ Needs tests, proper error handling, security hardening, and selector maintenance strategy

The foundation is strong. The gaps are fixable.

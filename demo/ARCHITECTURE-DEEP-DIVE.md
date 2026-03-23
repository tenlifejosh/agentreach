# AgentReach — Architecture Deep Dive

**Version:** 0.3.0  
**Audience:** Senior engineers familiar with browser automation, auth systems, and security architecture.

---

## System Overview

AgentReach is a single-machine, local-first tool. It has no server component, no network daemon, no cloud dependency. All state lives encrypted on the user's disk. Operations are synchronous from the user's perspective (CLI) and async internally (Playwright requires an event loop).

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Machine                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  CLI (typer) │───▶│   Drivers    │───▶│  Browser Layer   │  │
│  │  agentreach  │    │  kdp/etsy/   │    │  Playwright +    │  │
│  │              │    │  gumroad/... │    │  stealth_async   │  │
│  └──────────────┘    └──────┬───────┘    └────────┬─────────┘  │
│                             │                     │            │
│                      ┌──────▼───────┐   ┌─────────▼─────────┐ │
│                      │  Vault Layer │   │  Headless Chromium │ │
│                      │  Fernet/AES  │   │  (per operation)   │ │
│                      │  ~/.agent... │   └───────────────────-┘ │
│                      └─────────────-┘                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼───────────┐
                    │  Platform Servers   │
                    │  KDP / Etsy /       │
                    │  Gumroad / Reddit / │
                    │  Twitter / etc.     │
                    └─────────────────────┘
```

---

## Data Flow: Harvest Phase (One-Time Setup)

```
Human
  │
  │  runs: agentreach harvest kdp
  │
  ▼
CLI (cli.py)
  │  calls harvest(platform, timeout)
  ▼
harvester.py
  │  1. Launch visible Chromium (headless=False)
  │  2. Navigate to LOGIN_URL[platform]
  │  3. Wait for POST_LOGIN_URL_PATTERN match
  │     (human logs in manually during this wait)
  │  4. [KDP only] Wait for deep-auth URL (title creation form)
  │  5. Call context.cookies()  → all cookies, including HttpOnly
  │  6. Call context.storage_state() → cookies + localStorage
  │  7. Close browser
  ▼
store.py (SessionVault.save)
  │  1. json.dumps(session_data)
  │  2. Fernet.encrypt(payload)
  │      └─ AES-128-CBC + HMAC-SHA256
  │         key = PBKDF2(machine_uuid, random_salt, 480k iterations)
  │  3. Write to ~/.agentreach/vault/{platform}.vault
  ▼
Disk (encrypted at rest)
```

---

## Data Flow: Autonomous Operation Phase (Every Run)

```
Caller (agent / CLI / Python API)
  │
  │  async with platform_context("kdp") as (ctx, page):
  │      await page.goto("https://kdp.amazon.com/en_US/bookshelf")
  ▼
session.py (platform_context)
  │  1. vault.load(platform)
  │      └─ read bytes from disk
  │      └─ Fernet.decrypt(bytes)
  │      └─ json.loads(payload)
  │  2. check_session(platform) → verify health/expiry
  │  3. browser = await p.chromium.launch(headless=True)
  │  4. context = await browser.new_context(
  │         storage_state=saved_state,
  │         user_agent="Mozilla/5.0 ..."
  │     )
  │  5. page = await context.new_page()
  │  6. await stealth_async(page)  [if playwright-stealth installed]
  │  7. yield (context, page)
  │     │
  │     ▼
  │   [Driver code runs here: navigate, interact, extract data]
  │     │
  │     ▼
  │  8. browser.close()  [in finally block — always runs]
  ▼
Result returned to caller
```

---

## Data Flow: File Upload (Uploader)

```
Driver calls upload_file(page, file_path, ...)
  │
  ├─ Strategy 1: setInputFiles (CDP level)
  │     └─ CDP Input.setFiles → native browser file setter
  │     └─ Check: file.name in page.content() || input.files.length > 0
  │     └─ If success → return True
  │
  ├─ Strategy 2: Native HTMLInputElement.prototype.files setter
  │     └─ Read file bytes → base64 encode
  │     └─ page.evaluate(JS):
  │           atob(base64) → Uint8Array → Blob → File → DataTransfer
  │           Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'files').set.call(input, dt.files)
  │           input.dispatchEvent(new Event('change', {bubbles: true}))
  │     └─ If success → return True
  │
  ├─ Strategy 3: File Chooser Interception
  │     └─ page.expect_file_chooser()
  │     └─ page.click(trigger_selector)
  │     └─ CDP intercepts OS file dialog before it renders
  │     └─ file_chooser.set_files(path)
  │     └─ If success → return True
  │
  └─ Strategy 4: DragEvent simulation
        └─ Reconstruct File in JS (same base64 path as Strategy 2)
        └─ Construct DataTransfer with the File
        └─ Dispatch DragEvent('drop', {dataTransfer: dt}) on drop zone
        └─ If success → return True
  │
  └─ All failed → return False, log warning
```

---

## Security Boundary Analysis

### What is protected

| Asset | Protection | Mechanism |
|-------|-----------|-----------|
| Platform session cookies | Encrypted at rest | Fernet AES-128-CBC + HMAC-SHA256 |
| localStorage/sessionStorage | Encrypted at rest | Same |
| API tokens (Gumroad, Etsy) | Encrypted at rest | Same |
| Encryption key | Never stored | Derived at runtime from machine UUID + salt |
| Salt | Stored, but useless alone | ~/.agentreach/vault/.salt — worthless without MAC |

### What is NOT protected

| Threat | Status | Notes |
|--------|--------|-------|
| Physical access to machine while unlocked | **Not protected** | Attacker can derive key from running process memory or MAC address + salt file |
| Full-disk encryption bypass | **Not protected** — FDE required | AgentReach relies on OS/FDE for physical security |
| Memory forensics | **Not protected** | Decrypted session data lives in Python process memory during operations |
| Network interception | **Not applicable** | All traffic is HTTPS; AgentReach is not in the network path |
| Compromised Playwright / Chromium | **Not protected** | Supply chain attack on browser binary is out of scope |
| Other processes on same machine reading vault files | **Partially protected** | Vault files have standard file permissions; not using OS-level secret stores (Keychain, TPM) |

### Design decision: Why not macOS Keychain?

Using the OS keychain would require explicit user approval on each machine and complicates cross-user scenarios. The current design chooses consistency and portability over maximum security. For a tool that stores authentication sessions (not passwords), this is a reasonable tradeoff — but it should be understood by operators.

---

## Threat Model

### Adversarial scenarios and mitigations

**Scenario 1: Attacker obtains the encrypted vault file**

The attacker has `~/.agentreach/vault/kdp.vault`. Without the `.salt` file and the machine's MAC address, brute-force requires iterating all ~281 trillion 48-bit values through PBKDF2 at 480,000 iterations each. At 100,000 PBKDF2 hashes/second on modern hardware: ~281T / 100,000 = ~89 years. Practical MAC address space is smaller (NIC OUI ranges), but this remains computationally infeasible.

**Scenario 2: Attacker obtains vault file AND salt file**

Still requires MAC address. MAC addresses for real NIC hardware span assigned OUI ranges (~5000 vendors × 16M addresses each). Feasibility improves but remains impractical.

**Scenario 3: Attacker obtains vault file + salt + MAC address**

Key can be derived. Decryption is then a single operation. This is the scenario FDE prevents. AgentReach's cryptographic boundary stops here — FDE is the expected outer layer.

**Scenario 4: Platform detects automation**

The tool targets the user's own authenticated session on platforms they legitimately use. Detection risk exists (see FAQ). Mitigation: stealth patching, real session cookies (not constructed auth headers), user-agent spoofing.

**Scenario 5: Path traversal via platform name**

Mitigated by the `_path()` method's explicit character rejection + regex + resolved-path check (belt-and-suspenders). Tested in `test_edge_cases.py`.

**Scenario 6: Tampered vault file**

Fernet's HMAC-SHA256 covers the entire ciphertext. Any modification to the encrypted bytes causes `InvalidToken` on decryption — silent data corruption is not possible.

---

## Design Decisions

### Why Playwright instead of requests/httpx?

Platform login flows involve JavaScript execution, CSRF token extraction from dynamic pages, multi-step redirects, and sometimes Signed-in-with-Google flows that are implemented entirely in JavaScript. HTTP clients cannot handle these. Playwright runs a real browser.

### Why not use headless from the start?

For the harvest phase, there is no way around it: we need a human to authenticate. Forcing headless would require us to automate the login itself, which means handling CAPTCHA, 2FA, and platform-specific auth quirks for every platform. This is an infinite maintenance burden. One-time visible login + cookie replay is the right engineering tradeoff.

### Why Fernet instead of raw AES?

Fernet is an authenticated encryption scheme. It provides:
1. Confidentiality (AES-128-CBC)
2. Authentication (HMAC-SHA256) — tampered ciphertext raises `InvalidToken`
3. A timestamp in every token (enables replay attack detection if needed)
4. A well-tested, high-level API with no low-level IV management errors

Raw AES-CBC without proper authentication is vulnerable to padding oracle attacks. Fernet eliminates this class of bug.

### Why PBKDF2 and not scrypt/Argon2?

PBKDF2 is supported by Python's `cryptography` library on all platforms without native compiled dependencies. scrypt and Argon2 require native code that isn't universally available in all Python environments. PBKDF2 with 480k iterations is sufficient for this threat model (machine-bound key, not a standalone password).

### Why not store the key in macOS Keychain?

Cross-platform portability. The tool targets macOS and Linux. Keychain is macOS-only. SecretService (Linux) requires D-Bus and a running session manager, which breaks headless/server environments. The current design works everywhere `~/.agentreach/` is writable.

### Why 480,000 iterations and not more?

Key derivation happens once at module load time (`_FERNET = Fernet(_derive_key())`), not on every operation. Even 480k iterations adds only ~50-100ms of startup time. We chose 480k as the balance between security (well above OWASP's 2023 minimum of 310k for PBKDF2-SHA256) and fast startup. This is a known area for improvement — OWASP now recommends 600k.

### Why context managers for session handling?

```python
async with platform_context("kdp") as (ctx, page):
    ...
```

The `finally` block in `platform_context` guarantees `browser.close()` runs even if the driver code raises an exception. Without this, Playwright browser processes leak. Context managers enforce the cleanup contract.

---

## Comparison to Google's Internal Approaches

This is speculative — Google's internal tools are not public — but educated comparison based on known patterns:

### Session Management

**Google internally** likely uses: short-lived signed JWTs, service-to-service mTLS with SPIFFE identities, Credential Access Broker (CAB) patterns where humans authorize machine identities via Chubby/BorgMaster distributed locks.

**AgentReach**: Browser session cookies replayed into Playwright. Simpler, no infrastructure required, appropriate for consumer platforms that use browser auth.

The fundamental difference: Google's systems work with APIs they control. AgentReach works with web UIs it does not control. Cookie replay is the only option when there is no API.

### Cookie Replay

**Google Chrome** implements "Continue where you left off" via profile-level storage of encrypted cookies using the platform OS keychain (Windows DPAPI, macOS Keychain, Linux libsecret). Profile data is encrypted with a key stored in the keychain.

**AgentReach**: PBKDF2-derived key from MAC address + random salt. No OS keychain dependency. Weaker isolation (no TPM involvement) but portable.

### Browser Automation

**Google's WebDriver specification** (now W3C standard) was designed by Google engineers. Playwright is built on the Chrome DevTools Protocol, which Google developed. The mechanisms AgentReach uses — `DOM.setFileInputFiles`, `Page.fileChooserOpened` interception, `Network.setCookies` — are all Google-developed CDP commands.

AgentReach is, in a meaningful sense, using Google's own automation infrastructure to interact with Google's own products (via KDP on Amazon Chromium).

### Security Architecture

**Google internally**: Defense-in-depth with multiple layers — BeyondCorp Zero Trust, hardware security keys, short-lived credentials, audit logging to immutable append-only stores.

**AgentReach**: Single-layer encryption at rest. No audit logging. No credential rotation. **This is appropriate for an individual developer tool**, not appropriate for enterprise multi-user systems.

The design is honest about its scope: a developer tool for one person automating their own accounts. Scaling to multi-user enterprise would require a completely different architecture.

---

## What We'd Do Differently With Unlimited Time

### 1. OS Keychain integration
Store the vault encryption key in macOS Keychain / Linux SecretService / Windows DPAPI. This adds hardware-backed protection and eliminates the MAC-address dependency. The main cost: platform-specific code and complexity in headless environments.

### 2. Argon2id KDF instead of PBKDF2
Argon2id is memory-hard (resistant to GPU and ASIC brute-force). PBKDF2 is not. For standalone credential security, Argon2id is the correct choice.

### 3. TOTP-based re-authentication for sensitive operations
Before destructive operations (deleting a listing, publishing a book), require a TOTP code to be entered. This prevents a compromised process from abusing the vault without the human's knowledge.

### 4. Audit logging
Append-only log of every operation: timestamp, platform, action, result. Stored separately from the vault. Useful for debugging and for auditing "what did the agent do?"

### 5. Session refresh without full re-harvest
Some platforms (Reddit, Twitter) support OAuth token refresh. Instead of requiring full re-harvest, implement automatic token refresh when possible.

### 6. Structured retry with jitter
Current drivers attempt operations once and return success/failure. Production automation needs exponential backoff with jitter for transient errors, rate limiting awareness, and circuit breakers.

### 7. Selector versioning
Platform UIs change. When a selector breaks, the driver fails silently or with a confusing error. A versioned selector registry with platform-specific UI version detection would enable faster breakage detection and rollback.

### 8. WASM-isolated browser sandbox
For higher-trust environments, run the Playwright browser in a WASM sandbox rather than a full OS process. Reduces blast radius if the browser binary is compromised.

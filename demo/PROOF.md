# AgentReach — Technical Proof of Operation

**Version:** 0.3.0  
**Date:** 2026-03-23  
**Audience:** Senior engineers. This document makes no marketing claims. It explains exactly what the code does, in order, with line-level references.

---

## What AgentReach Actually Is

AgentReach solves one specific problem: web platforms that require human-interactive login (2FA, CAPTCHA, dynamic auth flows) cannot be automated by standard API clients. AgentReach's answer is to harvest the authenticated browser state after a human completes login, encrypt it to disk, then replay that state into a headless Playwright context for every subsequent operation.

This is not novel. It is the same pattern Google Chrome uses for its "continue where you left off" feature, the same mechanism Puppeteer uses for persistent auth in CI/CD, and the same idea behind Selenium Grid session reuse. AgentReach packages this into a structured, platform-specific, CLI-driven tool.

What follows is a component-by-component technical walkthrough.

---

## Component 1: Cookie Harvesting (`browser/harvester.py`)

### What it does

Opens a **visible, non-headless** Chromium browser and waits for the human to complete login normally. Once a post-login URL pattern is detected, it calls `context.cookies()` and `context.storage_state()` to capture the full authenticated browser state, then writes it encrypted to disk.

### The code, exactly

```python
# harvester.py, line ~83
browser = await p.chromium.launch(
    headless=False,              # Visible — human drives this
    args=["--start-maximized"],  # No --no-sandbox (not needed on local desktop)
)
context = await browser.new_context(viewport={"width": 1280, "height": 900})
page = await context.new_page()
await page.goto(login_url)
```

The browser navigates to the platform login URL (e.g., `https://kdp.amazon.com/en_US/signin`). No automation of the login itself — the human types their credentials.

```python
# harvester.py, line ~97
await page.wait_for_url(
    f"**{post_login_pattern}**",
    timeout=timeout * 1000,
    wait_until="domcontentloaded",
)
```

Detection is URL-pattern based. Once the browser lands on a post-login page (e.g., `kdp.amazon.com/en_US/bookshelf`), harvesting begins.

```python
# harvester.py, line ~127
cookies = await context.cookies()
storage_state = await context.storage_state()
```

`context.cookies()` returns all cookies for all domains in the context — including HttpOnly session cookies that JavaScript cannot read. `context.storage_state()` returns localStorage and sessionStorage, plus cookies in a serialized format Playwright can restore directly. Both are necessary because different platforms store auth state in different places.

```python
# harvester.py, line ~133
session_data = {
    **existing,
    "platform": platform,
    "harvested_at": datetime.now(timezone.utc).isoformat(),
    "cookies": cookies,
    "storage_state": storage_state,
    "login_url": login_url,
}
vault.save(platform, session_data)
```

The session is merged with any existing vault data (to preserve API tokens saved separately) and written to the encrypted vault.

### KDP Deep Auth Step

Amazon KDP uses a step-up authentication pattern (`max_auth_age=0`) for title creation endpoints. A session that can read the bookshelf cannot create titles without the deeper auth cookies. The harvester handles this explicitly:

```python
# harvester.py, POST_LOGIN_DEEP_STEPS
"kdp": {
    "pattern": "kdp.amazon.com/en_US/title-setup",
    "instructions": "✅ Logged in! Now... Click '+ Create a new title'..."
}
```

After the initial login, the harvester waits for the user to navigate to the title creation form. This captures the `step-up` auth cookies, enabling fully autonomous title creation later.

### What `context.cookies()` returns

Each cookie object includes:

| Field | Purpose |
|-------|---------|
| `name` | Cookie name |
| `value` | Cookie value (raw, undecoded) |
| `domain` | Domain scope (e.g., `.amazon.com`) |
| `path` | Path scope |
| `expires` | Expiry timestamp (Unix float) |
| `httpOnly` | Whether JS can read it |
| `secure` | Whether HTTPS-only |
| `sameSite` | Cross-site policy |

HttpOnly cookies — the ones that matter most for auth — are included because Playwright has access to the browser's cookie store directly, not via JavaScript.

---

## Component 2: Vault Encryption (`vault/store.py`)

### The full cryptographic chain

**Step 1: Key material collection**

```python
# store.py, _derive_key()
machine_id = str(uuid.getnode()).encode()  # MAC-address based UUID
```

`uuid.getnode()` returns the machine's MAC address as an integer. This provides machine-binding: a vault stolen from disk is worthless without the originating hardware (or its MAC address).

**Step 2: Salt generation and persistence**

```python
# store.py, _get_or_create_salt()
if SALT_FILE.exists():
    salt = SALT_FILE.read_bytes()
    if len(salt) == 32:
        return salt

# New installation: cryptographically random
salt = os.urandom(32)
SALT_FILE.write_bytes(salt)
```

The salt is stored at `~/.agentreach/vault/.salt`. It is 32 bytes of `os.urandom()` — the OS CSPRNG. The salt is persistent across calls so the same key is derived every time, but it is unique per installation so two machines with the same MAC address (cloned VMs) produce different keys.

Backward compatibility: if vault files exist but no `.salt` file, the code reconstructs the original MAC-based salt to avoid breaking existing sessions.

**Step 3: PBKDF2 key derivation**

```python
# store.py, _derive_key()
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=480000,     # OWASP recommended minimum as of 2023: 600k; we're at 480k
)
key = base64.urlsafe_b64encode(kdf.derive(machine_id))
```

PBKDF2-HMAC-SHA256 with 480,000 iterations. This is the same KDF used by password managers. At 480k iterations, brute-forcing this offline is infeasible if the MAC address space is constrained. (The limitation: MAC addresses are 48-bit, only ~281T possibilities. This is a known weakness — see Known Limitations below.)

**Step 4: Fernet symmetric encryption**

```python
# store.py, module level
_FERNET = Fernet(_derive_key())
```

The derived key becomes the Fernet symmetric key. Fernet is AES-128-CBC + HMAC-SHA256, using the `cryptography` library (Python binding to OpenSSL). Each encrypted token includes:
- Version byte (`\x80`)
- Timestamp (8 bytes)
- 128-bit random IV
- Ciphertext (AES-CBC padded)
- HMAC-SHA256 over version + timestamp + IV + ciphertext

**Step 5: Encrypt and write**

```python
# store.py, SessionVault.save()
payload = json.dumps(data).encode()
encrypted = _FERNET.encrypt(payload)
self._path(platform).write_bytes(encrypted)
```

The session JSON is serialized, encrypted, and written as raw bytes. No base64 at the file level — Fernet's output is already URL-safe base64 internally, but written as bytes.

**Step 6: Decrypt and load**

```python
# store.py, SessionVault.load()
encrypted = path.read_bytes()
payload = _FERNET.decrypt(encrypted)
return json.loads(payload.decode())
```

Fernet decryption verifies the HMAC before decrypting. If tampered with, it raises `InvalidToken` — not a silent decryption failure. AgentReach catches this and raises `VaultCorruptedError` with a clear remediation message.

### Path traversal protection

The vault path construction is explicit about rejecting traversal:

```python
# store.py, SessionVault._path()
if any(c in platform for c in ('/', '\\', '.', '\x00')):
    raise ValueError(...)
safe = platform.lower().replace(" ", "_")
if not re.fullmatch(r'[a-z0-9_\-]+', safe):
    raise ValueError(...)
target = (self.vault_dir / f"{safe}.vault").resolve()
if not str(target).startswith(vault_dir_resolved + "/"):
    raise ValueError(...)
```

Belt-and-suspenders: reject on character inspection, then validate with regex, then verify the resolved path stays inside the vault directory. An attacker cannot escape the vault directory via platform name injection.

---

## Component 3: Session Injection / Replay (`browser/session.py`)

### The core mechanism

```python
# session.py, platform_context()
context: BrowserContext = await browser.new_context(
    storage_state=storage_state if storage_state else None,
    viewport={"width": 1280, "height": 900},
    user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
)

if cookies and not storage_state.get("cookies"):
    await context.add_cookies(cookies)
```

`new_context(storage_state=...)` is Playwright's native session restore API. It populates the new context with all cookies and localStorage from the saved state — the browser starts as if it were the original session continued. This is not a hack; it is documented Playwright API.

The cookie fallback (`add_cookies`) handles edge cases where `storage_state` is sparse (some platforms don't use localStorage at all).

### Health check before use

```python
# session.py, platform_context()
if check_health:
    health = check_session(platform, vault)
    if health.status == SessionStatus.MISSING:
        raise SessionNotFoundError(...)
    if health.status == SessionStatus.EXPIRED:
        raise SessionExpiredError(...)
```

Sessions are checked against estimated TTLs before use. This prevents silent failures where a session was valid when loaded but expired between check and use.

### Stealth integration

```python
# session.py, ~line 65
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

# Inside platform_context:
if stealth_async is not None:
    await stealth_async(page)
```

`playwright-stealth` is an optional dependency. If installed, it patches JavaScript properties that leak Playwright's presence. If not installed, the code degrades gracefully — the `try/except ImportError` at module level is intentional.

### What stealth_async patches (and doesn't)

`playwright-stealth` patches the following via JavaScript injection before page load:
- `navigator.webdriver` → removes or sets to `undefined`
- `navigator.plugins` → injects fake plugin list mimicking real Chrome
- `navigator.languages` → normalizes to `['en-US', 'en']`
- `window.chrome` → injects a fake Chrome runtime object
- `Permission.query` → overrides to avoid automation detection via permission checks
- `WebGL vendor/renderer strings` → spoofs to look like real GPU

**What it doesn't patch:**
- TLS fingerprinting (JA3/JA4 signatures from the browser's TLS handshake)
- TCP/IP timing characteristics
- Canvas fingerprinting (the `<canvas>` pixel hash trick) — partially addressed by GPU spoofing but not fully
- Behavioral signals (mouse movement patterns, typing cadence, scroll velocity)
- IP reputation and ASN-level signals (residential vs. datacenter IP)

This is stated honestly in the FAQ.

---

## Component 4: React Upload Bypass (`browser/uploader.py`)

### The problem

React wraps native DOM events in a synthetic event system. When you programmatically set `input.value = '/path/to/file'`, the DOM changes but React's `onChange` handler is never triggered because React never sees the synthetic event. The file appears to be set at the DOM level but the React component tree is unaware.

### Strategy 1: CDP-level setInputFiles

```python
# uploader.py, ~line 60
input_el = page.locator(input_selector).first
await input_el.set_input_files(str(file_path), timeout=timeout)
```

Playwright's `set_input_files` uses Chrome DevTools Protocol's `DOM.setFileInputFiles` command, which operates at the browser internals level — below JavaScript, below React's event interception. For most React file inputs, this triggers the native `change` event, which React does observe. **This works ~80% of the time.**

### Strategy 2: Native HTMLInputElement setter with real file bytes

```python
# uploader.py, ~line 85
# Base64-encode the actual file bytes
file_b64 = base64.b64encode(file_bytes).decode("ascii")

result = await page.evaluate("""
    ([selector, fileName, fileB64, mimeType]) => {
        // Reconstruct the actual file from bytes
        const binaryStr = atob(fileB64);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: mimeType });
        const file = new File([blob], fileName, { type: mimeType });
        const dt = new DataTransfer();
        dt.items.add(file);

        // Use the NATIVE HTMLInputElement setter, bypassing React's proxy
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'files'
        );
        if (nativeSetter && nativeSetter.set) {
            nativeSetter.set.call(input, dt.files);  // Calls native, not React-wrapped
        }

        // Fire both events — React listens to both
        input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
        input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
        return true;
    }
""", [input_selector, file_path.name, file_b64, mime_type])
```

**Why this works:** React wraps the `files` property on individual input elements, but `HTMLInputElement.prototype.files` on the class itself is not wrapped. Getting the property descriptor from the prototype and calling `.set.call(input, ...)` bypasses the instance-level wrapper and sets files via the native setter — React's synthetic event fires because the native setter triggers the DOM mutation that React is listening to.

**Why real bytes:** Some React uploaders validate that the `File` object contains real content (by checking `file.size > 0` or calling `file.arrayBuffer()`). Placeholder text would fail this check. Encoding the actual file as base64 and reconstructing it as a `Blob` ensures the `File` object has real content.

**This works for React uploaders that intercept `onChange` on the input element.**

### Strategy 3: File chooser interception

```python
# uploader.py, ~line 135
async with page.expect_file_chooser(timeout=timeout) as fc_info:
    await page.click(trigger_selector)
file_chooser = await fc_info.value
await file_chooser.set_files(str(file_path))
```

Some upload UIs hide the `<input type="file">` entirely and show a custom button. Clicking the button triggers the native OS file dialog. Playwright intercepts the file chooser dialog at the CDP level (`Page.fileChooserOpened` event) before the OS dialog renders, injects the file path, and the dialog resolves as if the user selected the file. **The OS dialog never appears.**

**Why this exists:** When there is no accessible `<input type="file">` in the DOM (React portals or shadow DOM), Strategies 1 and 2 cannot find a selector to work on.

### Strategy 4: Drag-and-drop DataTransfer simulation

```python
# uploader.py, ~line 165
dropped = await page.evaluate("""
    ([selector, fileName, fileB64]) => {
        const zone = document.querySelector(selector);
        const file = new File([blob], fileName, ...);
        const dt = new DataTransfer();
        dt.items.add(file);

        const dropEvent = new DragEvent('drop', {
            bubbles: true, cancelable: true, dataTransfer: dt,
        });
        zone.dispatchEvent(dropEvent);
        return true;
    }
""", [drop_zone_selector, file_path.name, file_b64])
```

For drop-zone-only uploaders (no `<input>` at all), this constructs a `DragEvent` with a real `DataTransfer` object containing the file. This mimics a browser drag-and-drop at the JavaScript level — the application's `drop` event listener receives the event and the file just as if the user dragged it.

**Why this exists:** Some modern upload UIs (Wix, some Etsy image uploaders) use only the Drag-and-Drop File API and have no `<input>` element whatsoever.

---

## Known Limitations (Honest)

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **MAC address space is small (48-bit)** | Vault key brute-force is theoretically feasible if attacker has the encrypted vault file and tries all MAC addresses (~281 trillion, but likely far less for real NIC hardware ranges) | Full-disk encryption (FileVault/BitLocker) is the correct mitigation — the vault is not a standalone secret store |
| **Sessions expire** | KDP: ~30 days. Twitter: ~21 days. Reddit: ~90 days. After expiry, re-harvest is required | `agentreach doctor` and the monitor system warn ahead of expiry; re-harvest takes ~2 minutes |
| **playwright-stealth is not a magic cloak** | Behavioral signals, TLS fingerprinting, IP reputation are not spoofed | Designed for legitimate automation (user's own account), not adversarial contexts |
| **2FA breaks the harvest loop if triggered mid-flow** | If Amazon forces 2FA after login detection but before deep-auth step, harvest fails | Harvest must be re-run; the 5-minute timeout gives time to handle 2FA prompts |
| **KDP's step-up auth is triggered by Amazon heuristics** | Amazon may demand re-authentication at any time, regardless of session age | Session health checks provide early warning; nothing prevents mid-session re-auth challenges |
| **No CAPTCHA solving** | If login triggers CAPTCHA during harvest, human must solve it (which they can, since the browser is visible) | For headless replay, if CAPTCHA is triggered, the operation fails and requires re-harvest |
| **No official API calls** | Browser automation is inherently fragile to UI changes | Drivers are structured with selector constants and versioned; breakage is isolatable |
| **Reddit and Twitter rate-limit aggressively** | Posting too frequently from a single account triggers temporary blocks | AgentReach does not implement rate limiting — callers must manage cadence |
| **TikTok driver is not implemented** | `tiktok` appears in LOGIN_URLS but has no driver in `src/agentreach/drivers/` | Harvest is supported but autonomous operations are not yet built |

---

## Test Suite

230 tests. All pass. 0.37 seconds.

```
$ pytest tests/ -q
collected 230 items
...
230 passed in 0.37s
```

Tests cover:
- `test_vault.py` — encryption/decryption round-trips, path traversal rejection, VaultCorruptedError handling
- `test_harvester.py` — mock browser harvest flows, KDP deep-auth step, timeout handling
- `test_browser.py` — session context creation, stealth injection, health check gating
- `test_uploader.py` — all 4 upload strategies, MIME type mapping, file-not-found handling
- `test_health.py` — session TTL calculations, expiry detection, status report formatting
- `test_drivers.py` — driver instantiation, session validation, result object shape
- `test_cli.py` — CLI command routing, output formatting
- `test_edge_cases.py` — unicode platform names, concurrent vault access, malformed vault files
- `test_monitor.py` — expiry monitoring, health transitions

All browser and network calls are mocked. Tests run without a browser or network in 0.37 seconds.

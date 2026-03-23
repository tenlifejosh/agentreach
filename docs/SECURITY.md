# AgentReach Security Model

---

## What AgentReach Stores

AgentReach stores two kinds of secrets:

**Browser sessions** (KDP, Pinterest, Reddit, X/Twitter, Nextdoor):
- Full browser cookie sets from the authenticated platform domain
- Include session tokens, CSRF tokens, and any auth cookies set after login
- Stored as a JSON array in the Fernet-encrypted vault

**API credentials** (Etsy, Gumroad):
- OAuth access tokens or API keys
- Shop/account IDs
- Stored as JSON fields in the Fernet-encrypted vault

---

## Encryption

### Algorithm

Each vault file is encrypted with **Fernet** from the Python `cryptography` library.

Fernet is a composition of:
- **AES-256-CBC** for symmetric encryption
- **HMAC-SHA256** for authentication
- A **random 128-bit IV** generated per encryption operation

This provides authenticated encryption — the data is both encrypted and tamper-evident. An attacker who modifies a vault file will cause decryption to fail rather than silently produce garbage data.

### Key Derivation

The encryption key is derived at runtime from the machine's MAC address (network interface hardware ID):

```python
machine_id = str(uuid.getnode()).encode()   # MAC address as integer → bytes
salt = hashlib.sha256(machine_id).digest()  # deterministic 32-byte salt
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=480000,
)
key = base64.urlsafe_b64encode(kdf.derive(machine_id))
```

**PBKDF2** with 480,000 iterations makes brute-force attacks expensive. As of 2026, NIST recommends ≥ 210,000 iterations for SHA-256; 480,000 exceeds this.

**Key is non-portable by design.** A vault file copied to another machine cannot be decrypted — the MAC address will differ, producing a different key. This is intentional: it prevents credential exfiltration via file copy.

### Key Caching

The key is derived once at module import (`_FERNET = Fernet(_derive_key())`) and cached in memory for the process lifetime. Each CLI invocation is a new process, so each invocation re-derives the key.

---

## Vault File Storage

```
~/.agentreach/vault/
├── kdp.vault
├── etsy.vault
├── gumroad.vault
└── ...
```

Files are owned by the current user. Default permissions on macOS/Linux: `600` (owner read/write only) when created via Python's `Path.write_bytes()` — though this depends on the process umask.

**Recommendation:** Verify vault file permissions periodically:
```bash
ls -la ~/.agentreach/vault/
# Should show: -rw------- (600) for each .vault file
```

If permissions are wrong, fix them:
```bash
chmod 600 ~/.agentreach/vault/*.vault
chmod 700 ~/.agentreach/vault/
```

---

## Threat Model

### Threat 1: File Exfiltration

**Scenario:** An attacker copies your `.vault` files to another machine.

**Mitigation:** The vault is encrypted with a machine-specific key. Files copied elsewhere cannot be decrypted without the source machine's MAC address.

**Residual risk:** If the attacker also knows (or can guess) your MAC address, they can reconstruct the key. MAC addresses are broadcast on local networks and are often predictable (OUI prefix + sequential suffix). This is a known limitation.

**Severity for local desktop use:** Low. The attacker would need both the vault files AND knowledge of your MAC address.

### Threat 2: Local Machine Compromise (Root)

**Scenario:** An attacker with root access on your machine.

**Mitigation:** None that matters. Root can read `/sys/class/net/*/address`, reconstruct the key, and decrypt any vault file. The encryption model provides no protection against local root.

**This is not a design flaw.** AgentReach is a local tool. It's not designed to protect against attackers who already own the machine.

### Threat 3: Memory Exposure

**Scenario:** Memory dump or swap file captures decrypted credentials.

**Mitigation:** Minimal. Python's garbage collector does not zero memory. Decrypted session data (cookies, tokens) lives in memory as Python strings/dicts for the duration of each operation.

**Severity for local desktop use:** Low. Requires specific conditions (swap enabled, memory dump tool available, timing precision).

### Threat 4: Key Derivation Instability

**Scenario:** Your MAC address changes (new network card, VM re-provisioning, VirtualBox network reset).

**Effect:** The vault key changes. Existing `.vault` files become permanently unreadable. You will need to re-harvest all sessions.

**When this happens:**
- Replacing a network interface card
- VM snapshot restore on a different host
- VirtualBox/Docker bridge network changes
- Some Wi-Fi cards on macOS (privacy MAC randomization — though `uuid.getnode()` uses the real MAC)

**Mitigation:** Keep a backup (`agentreach backup`) before any hardware changes. Restoring from backup on the same machine will work if the MAC hasn't changed yet.

### Threat 5: Supply Chain — `playwright-stealth`

`playwright-stealth` (2.0.2) is a community package with no formal security review. It injects JavaScript into every browser page. In theory, a compromised version of this package could exfiltrate cookies by injecting malicious JS into the authenticated page context.

**Probability:** Very low. PyPI package compromise is uncommon.

**Severity:** High. If it happened, all harvested sessions would be compromised.

**Current status:** `playwright-stealth` is not in AgentReach's declared dependencies. It's used if installed, silently skipped if not. This means most users don't have it installed by default.

### Threat 6: Platform-Specific Session Theft

**Scenario:** A platform serves malicious JavaScript that exfiltrates cookies from the headless context.

**Current state:** The harvester disables Chromium's sandbox (`--no-sandbox`). This removes one layer of isolation between the browser process and the OS.

**Recommendation:** The `--no-sandbox` flag should be removed for local desktop use. It was likely added for CI compatibility. The risk is low in practice but unnecessary.

---

## What AgentReach Does NOT Do

- Does not send credentials to any AgentReach server — there is no server
- Does not log credentials in plaintext anywhere
- Does not transmit any data except to the target platform
- Does not persist beyond the `~/.agentreach/` directory

---

## Backup Security

`agentreach backup` creates a `.enc` file encrypted with the same machine-specific Fernet key.

**Implications:**
- Backups can only be restored on the same machine (same MAC address)
- Backups are not portable disaster recovery — they're protection against accidental file deletion
- If your machine is destroyed, the backup is unrecoverable without the original MAC address

If you need portable backup, you would need to re-harvest sessions after hardware replacement. There is no current mechanism for portable cross-machine backup — this is a planned improvement for a future version.

---

## Security Improvement Roadmap

These are known weaknesses being tracked for future versions:

| Issue | Severity | Status |
|---|---|---|
| MAC address key derivation (predictable) | Medium | Planned: add separate random salt file |
| Path traversal in vault `_path()` | Medium | Planned: add `re.sub` sanitization |
| `--no-sandbox` in harvester | Low | Planned: remove for local use |
| Vault `load()` swallows decryption errors | Medium | Planned: surface specific error |
| `playwright-stealth` undeclared dependency | Low | Planned: add to `pyproject.toml` |

---

## Reporting Security Issues

Open a GitHub issue with the title `[Security]` or email `josh@tenlifecreatives.com` directly. Do not publicly disclose session extraction vulnerabilities without giving 30 days for a fix.

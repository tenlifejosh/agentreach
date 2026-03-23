# AgentReach — 5-Minute Getting Started Guide

This guide takes you from zero to posting real content on a real platform.

**Time to complete:** ~5 minutes (plus however long it takes you to log in to the platform)

---

## Before You Start

You need:
- Python 3.10 or newer
- A terminal
- A browser (Playwright will use Chromium)
- An account on at least one supported platform

---

## Step 1: Install (1 minute)

```bash
pip install agentreach
playwright install chromium
```

Verify it worked:

```bash
agentreach --version
# AgentReach v0.2.1

agentreach doctor
# Runs a full system check
```

---

## Step 2: Choose Your Platform

| If you want to... | Use this platform |
|---|---|
| Publish books | `kdp` |
| Sell digital downloads | `gumroad` or `etsy` |
| Post pins | `pinterest` |
| Post to Reddit | `reddit` |
| Post tweets | `twitter` |
| Post to your neighborhood | `nextdoor` |

---

## Step 3: Harvest a Session

This is the one-time setup for each platform. It opens a real browser window — you log in normally, then AgentReach captures the session automatically.

```bash
agentreach harvest kdp
```

A browser window will open. Log in to your KDP account. AgentReach is watching for you to land on the KDP bookshelf or dashboard. Once it detects you're logged in, it captures your session and closes the browser.

**What just happened:** Your login cookies are now encrypted and stored at `~/.agentreach/vault/kdp.vault`. You won't need to do this again for several weeks.

> **KDP users only:** After logging in to the main KDP dashboard, navigate to **Bookshelf → Add a new title → Paperback**. This ensures the session captures the elevated-auth cookies required for uploads. If you skip this step, `kdp upload` may fail with a step-up authentication error.

---

## Step 4: Verify the Session

```bash
agentreach verify kdp
# ✅ KDP session is valid.
```

Or check all platforms at once:

```bash
agentreach status
```

---

## Step 5: Do Something Real

### Publish a KDP paperback

```bash
agentreach kdp upload \
  --manuscript interior.pdf \
  --cover cover.pdf \
  --title "My Book Title" \
  --author "Your Name" \
  --price 12.99
```

### Tweet something

```bash
agentreach harvest twitter    # one-time setup

agentreach twitter tweet "Just shipped something new. AgentReach is live."
```

### Post to Reddit

```bash
agentreach harvest reddit     # one-time setup

agentreach reddit post MachineLearning \
  "I built a tool to give AI agents persistent web access" \
  "Here's how it works..."
```

### Save a Gumroad token and check sales

```bash
agentreach gumroad set-token YOUR_ACCESS_TOKEN
agentreach gumroad sales
```

Get your Gumroad access token from: **Gumroad Settings → Advanced → Access Token**

### Publish to Etsy

```bash
# One-time setup
agentreach etsy set-credentials \
  --api-key YOUR_ETSY_API_KEY \
  --access-token YOUR_ACCESS_TOKEN \
  --shop-id YOUR_SHOP_ID

# Publish a listing
agentreach etsy publish \
  --title "Printable Planner 2026" \
  --description "A beautiful daily planner..." \
  --price 4.99 \
  --digital-file planner.pdf \
  --images cover.jpg,preview.jpg \
  --tags "planner,printable,digital"
```

---

## Session Maintenance

Sessions expire. AgentReach estimates when that will happen and warns you in advance.

```bash
agentreach status          # See all sessions and days remaining
agentreach doctor          # Full diagnostics with recommended actions
```

When a session expires:

```bash
agentreach harvest kdp     # Re-harvest (same process as initial setup)
```

Sessions typically last:
- KDP: ~30 days
- Etsy/Gumroad API tokens: 60–90 days (depends on your settings)
- Pinterest: ~30 days
- Reddit: ~30 days (often longer in practice)
- Twitter/X: varies widely — re-harvest if it stops working

---

## Backup Your Sessions

```bash
agentreach backup
# ✅ Vault backed up: ~/.agentreach/backups/vault-2026-03-23.enc
```

The backup is encrypted with the same machine-specific key. It can only be restored on the same machine. Use it to recover from accidental vault deletion — not for moving to a new machine (re-harvest instead).

```bash
agentreach restore ~/.agentreach/backups/vault-2026-03-23.enc
```

---

## Troubleshooting

**`agentreach doctor` shows a driver failed to load:**
```bash
pip install agentreach --upgrade
```

**`agentreach verify kdp` says session is invalid but I just harvested:**

KDP may have required step-up auth. Re-harvest and make sure to navigate to the new title form before the harvester times out:
1. Log in to KDP
2. Click **Bookshelf → Paperback actions → Add new title**
3. Wait for the title-setup form to load
4. AgentReach will detect the URL and capture the session

**`agentreach kdp upload` fails with step-up auth error:**

Same as above. Re-harvest with the elevated session.

**Command not found after `pip install agentreach`:**

Make sure your Python scripts directory is on your PATH:
```bash
which agentreach
python -m agentreach --version   # fallback
```

**Playwright browser not found:**
```bash
playwright install chromium
```

---

## What's Next

- [CLI Reference](../README.md#cli-reference) — every command and option
- [Architecture](ARCHITECTURE.md) — how AgentReach works internally
- [Building a Driver](DRIVERS.md) — add support for a new platform
- [Security Model](SECURITY.md) — how your credentials are protected

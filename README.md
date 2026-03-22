# AgentReach 🦾

**Never ask a human to open a browser again.**

[![GitHub stars](https://img.shields.io/github/stars/tenlifejosh/agentreach?style=social)](https://github.com/tenlifejosh/agentreach/stargazers)
![Version](https://img.shields.io/badge/version-0.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)

AgentReach gives AI agents persistent, authenticated access to any web platform — KDP, Etsy, Gumroad, Pinterest, and beyond. One 10-minute bootstrap session. Autonomous forever after.

---

## ⭐ Star this repo if AgentReach solves a problem you've hit.
## 💖 [Sponsor the project](https://github.com/sponsors/tenlifejosh) to support ongoing development.

---

## The Problem

Every AI agent hits the same wall:

```
Agent: "I'll publish your product to Amazon KDP."
Reality: *needs browser relay* *needs logged-in session* *file upload fails* *relay disconnects*
```

The agent isn't dumb. The infrastructure just isn't there. Authentication dies when the human walks away. File uploaders reject programmatic input. Sessions expire with no recovery path. Every platform is a silo.

**AgentReach fixes this at the root.**

---

## Real-World Use Cases

**For digital product sellers:**
> "I told my AI agent to publish my new journal to KDP, Etsy, and Gumroad — all three — while I was at my kid's soccer game. Everything was live when I got back."

**For content creators:**
> "My agent posts to Pinterest every day at 9am. I haven't touched Pinterest manually in two months."

**For AI developers:**
> "I stopped building one-off browser automations and just use AgentReach. All my sessions in one vault, one API call to any platform."

**For agencies:**
> "We manage 12 clients' digital product stores. AgentReach handles all the uploads. We focus on strategy."

---

## How It Works

### 1. Bootstrap (once, ~10 minutes)
```bash
agentreach harvest --platform kdp
# Opens a real browser window. You log in normally.
# AgentReach saves your encrypted session. You're done.
```

### 2. Forever After (autonomous)
```bash
agentreach upload --platform kdp --manuscript interior.pdf --cover cover.pdf --title "My Book"
agentreach publish --platform etsy --product ./my-product/
agentreach post --platform pinterest --image pin.jpg --description "..." --link https://...
```

No human. No relay. No browser window. Just results.

---

## Features

- **🔐 Encrypted Session Vault** — AES-256 encrypted cookie + token storage. Sessions stored locally, never transmitted.
- **🤖 Headless Platform Drivers** — Playwright-powered drivers for KDP, Etsy, Gumroad, Pinterest. Loads saved sessions, operates fully headless.
- **📁 React Upload Bypass** — Solves the #1 file upload failure mode: React synthetic event systems rejecting programmatic input. Works on KDP, Etsy, and any React-based uploader.
- **♻️ Session Auto-Recovery** — Health checks detect expired sessions before they cause failures. Proactive alerts give you time to re-harvest before anything breaks.
- **🔌 OpenClaw Skill** — Drop-in skill for OpenClaw agents. `agentreach` commands available directly in agent context.
- **📦 Platform-Agnostic Core** — Add any platform by subclassing `BasePlatformDriver`. Built to extend.

---

## Supported Platforms

| Platform | Upload Files | Create Listings | Check Status | Post Content |
|----------|-------------|-----------------|--------------|--------------|
| Amazon KDP | ✅ | ✅ | ✅ | — |
| Etsy | ✅ | ✅ | ✅ | — |
| Gumroad | ✅ | ✅ | ✅ | — |
| Pinterest | — | — | — | ✅ |
| *LinkedIn, Shopify, YouTube, Substack* | *Pro* | *Pro* | *Pro* | *Pro* |
| *More via community drivers* | | | | |

---

## AgentReach vs Alternatives

| | AgentReach | Browser Use / Stagehand | Playwright (DIY) | RPA Tools |
|--|--|--|--|--|
| Works without API | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Session persistence | ✅ Built-in vault | ❌ Manual | ❌ Manual | ⚠️ Varies |
| React upload bypass | ✅ Solved | ❌ Common failure | ❌ Manual | ⚠️ Varies |
| Platform drivers | ✅ KDP, Etsy, Gumroad, Pinterest | ❌ DIY | ❌ DIY | ⚠️ Varies |
| OpenClaw integration | ✅ Native skill | ❌ No | ❌ No | ❌ No |
| Setup time | ✅ 10 min | ⚠️ Hours | ❌ Days | ❌ Days |
| Cost | ✅ Free (MIT) | ⚠️ Usage-based | ✅ Free | ❌ Expensive |

---

## Installation

```bash
pip install agentreach
# or from source:
git clone https://github.com/tenlifejosh/agentreach
cd agentreach
pip install -e .
```

**Requirements:** Python 3.10+, Playwright

```bash
playwright install chromium
```

📖 **[Full Getting Started Guide →](docs/GETTING-STARTED.md)**

---

## Quick Start

### Bootstrap a platform
```bash
# Opens real browser for you to log in. Saves session automatically.
agentreach harvest kdp
agentreach harvest etsy
agentreach harvest gumroad
agentreach harvest pinterest
```

### Check session health
```bash
agentreach status
# KDP        ✅ healthy  (expires in 23 days)
# Etsy       ✅ healthy  (expires in 45 days)
# Gumroad    ⚠️  expires in 3 days — run: agentreach harvest gumroad
# Pinterest  ✅ healthy  (expires in 60 days)
```

### Upload to KDP
```bash
agentreach kdp upload \
  --manuscript ./interior.pdf \
  --cover ./cover-full-wrap.pdf \
  --title "My Book Title" \
  --subtitle "My Subtitle" \
  --description "HTML description here" \
  --price 12.99 \
  --keywords "keyword1,keyword2,keyword3"
```

### Publish to Etsy
```bash
agentreach etsy publish \
  --product-dir ./my-product/ \
  --listing-file etsy-listing.md \
  --digital-file product.pdf \
  --mockups mockup-1.jpg,mockup-2.jpg,mockup-3.jpg
```

### Post to Pinterest
```bash
agentreach pinterest post \
  --image pin.jpg \
  --title "Pin Title" \
  --description "Pin description" \
  --link "https://amazon.com/dp/XXXXX" \
  --board "Faith Journals"
```

---

## OpenClaw Integration

Drop `agentreach` in your OpenClaw workspace skills folder and agents get native access:

```
# In agent context:
Use agentreach to upload interior.pdf and cover.pdf to KDP with title "Pray Bold"
```

See `skills/agentreach/SKILL.md` for full agent usage docs.

---

## Built With AgentReach

_Using AgentReach in production? [Open a PR](https://github.com/tenlifejosh/agentreach/pulls) to add your project here._

| Project | Use Case | By |
|---------|----------|----|
| [Ten Life Creatives](https://tenlifecreatives.com) | Digital product publishing to KDP, Etsy, Gumroad | @tenlifejosh |
| *Your project here* | *Your use case* | *You* |

---

## Security

- Sessions stored at `~/.agentreach/vault/` (AES-256 encrypted)
- Encryption key derived from machine UUID — vault is machine-specific
- No credentials ever leave your machine
- No cloud sync, no telemetry
- Vault file is gitignored by default

---

## Architecture

```
agentreach/
├── src/agentreach/
│   ├── vault/           # Encrypted session storage
│   │   ├── store.py     # VaultStore — read/write encrypted sessions
│   │   └── health.py    # SessionHealth — expiry detection + alerts
│   ├── browser/         # Headless browser management
│   │   ├── harvester.py # Cookie harvest via visible browser login
│   │   ├── session.py   # Load saved sessions into headless context
│   │   └── uploader.py  # React-bypass file upload engine
│   ├── drivers/         # Platform-specific drivers
│   │   ├── base.py      # BasePlatformDriver
│   │   ├── kdp.py       # Amazon KDP driver
│   │   ├── etsy.py      # Etsy driver
│   │   ├── gumroad.py   # Gumroad driver (API-first, cookie fallback)
│   │   └── pinterest.py # Pinterest driver
│   ├── api/             # Optional local HTTP API
│   │   └── server.py    # FastAPI server for agent integration
│   └── cli.py           # Typer CLI
├── skills/agentreach/   # OpenClaw skill
└── tests/
```

---

## Contributing

AgentReach is MIT licensed. PRs welcome.

**Priority community drivers:** LinkedIn, Shopify, Substack, Medium, YouTube Studio

**How to add a platform:**
1. Subclass `BasePlatformDriver`
2. Implement `harvest()`, `verify_session()`, and your platform's action methods
3. Register in `drivers/__init__.py`
4. Submit a PR

---

## Why We Built This

We're building digital products with an AI agent (Hutch, powered by [OpenClaw](https://openclaw.ai)). Every day, the agent would build something great and then hit a wall — a login screen, a file uploader, a session that died overnight.

The agent wasn't the problem. The plumbing was.

AgentReach is that plumbing. Build it once, open source it, and let every agent builder stand on it.

---

## Pro Tier

Need cloud session sync, team vaults, or custom platform drivers?

📄 **[See COMMERCIAL.md for Pro & Enterprise →](COMMERCIAL.md)**

---

## License

MIT © Ten Life Creatives — Joshua Noreen

---

*Built by [Ten Life Creatives](https://tenlifecreatives.com). Powered by [OpenClaw](https://openclaw.ai).*

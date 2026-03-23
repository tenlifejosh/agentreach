# AgentReach Skill

## What This Does
Gives OpenClaw agents persistent, authenticated access to web platforms without requiring a live browser relay or human present.

Supported platforms: **KDP**, **Etsy**, **Gumroad**, **Pinterest**

## Setup (One Time)

Install AgentReach:
```bash
cd /Users/oliverhutchins1/.openclaw/workspace-main/projects/agentreach
pip install -e .
playwright install chromium
```

Bootstrap each platform (requires human present for ~2 min per platform):
```bash
agentreach harvest kdp
agentreach harvest etsy
agentreach harvest gumroad
agentreach harvest pinterest
```

## Check Session Health
```bash
agentreach status
```

## Commands Available to Agents

### Amazon KDP
```bash
# Upload a new paperback
agentreach kdp upload \
  --manuscript /path/to/interior.pdf \
  --cover /path/to/cover-full-wrap.pdf \
  --title "Book Title" \
  --subtitle "Subtitle" \
  --description "<p>HTML description</p>" \
  --price 12.99 \
  --keywords "keyword1,keyword2,keyword3"

# Check bookshelf
agentreach kdp bookshelf
```

### Gumroad
```bash
# Save API token (one time)
agentreach gumroad set-token YOUR_TOKEN_HERE

# Publish a digital product
agentreach gumroad publish \
  --name "Product Name" \
  --description "Description" \
  --price 7.99 \
  --file /path/to/product.pdf

# Check sales
agentreach gumroad sales
agentreach gumroad sales --after 2026-03-01
```

### Etsy
```bash
# Save credentials (one time)
agentreach etsy set-credentials \
  --api-key YOUR_KEY \
  --access-token YOUR_TOKEN \
  --shop-id YOUR_SHOP_ID

# Publish listing
agentreach etsy publish \
  --title "Listing Title" \
  --description "Description" \
  --price 7.99 \
  --digital-file /path/to/product.pdf \
  --images "mockup1.jpg,mockup2.jpg,mockup3.jpg" \
  --tags "tag1,tag2,tag3"
```

### Pinterest
```bash
# Post a pin (requires harvested session)
agentreach pinterest pin \
  --title "Pin Title" \
  --description "Description" \
  --image /path/to/image.jpg \
  --link "https://amazon.com/dp/XXXXX" \
  --board "Faith Journals"
```

## How Sessions Work
- Sessions harvested once and stored encrypted at `~/.agentreach/vault/`
- Encryption is machine-specific (AES-128-CBC via Fernet, key derived from machine UUID)
- Sessions typically last 30-60 days
- Run `agentreach status` to see expiry dates
- Re-harvest when a session expires (~2 min per platform)

## Notes for Agents
- Always check `agentreach status` before attempting uploads
- If a session shows EXPIRED or MISSING, alert the user — do not proceed
- Gumroad uses REST API (most reliable), KDP/Pinterest use headless browser
- File paths must be absolute or relative to the workspace

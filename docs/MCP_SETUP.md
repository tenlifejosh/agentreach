# AgentReach MCP Server — Setup Guide

AgentReach exposes its encrypted session vault and headless platform drivers as
**MCP (Model Context Protocol)** tools. This means Claude Desktop, Cursor, Continue,
Zed, and any other MCP-compatible host can drive KDP, Etsy, Gumroad, Pinterest,
Reddit, Nextdoor, and Twitter/X — fully autonomously — using natural language.

---

## What the MCP Server Exposes

### 🔧 Tools (6)

| Tool | Description |
|------|-------------|
| `vault_status` | List all stored sessions with harvest date and estimated expiry |
| `vault_health` | Full health check — healthy / expiring / expired / missing per platform |
| `platform_login` | Verify a session is live via headless browser check |
| `harvest_session` | Guide the user through one-time login harvest for a platform |
| `driver_list` | List available platform drivers and their supported actions |
| `platform_action` | **Execute any driver action** — post, upload, publish, list products, etc. |

### 📁 Resources (3)

| URI | Description |
|-----|-------------|
| `agentreach://vault/status` | Live vault health as JSON |
| `agentreach://drivers` | All driver capabilities as JSON |
| `agentreach://vault/{platform}` | Health metadata for a single platform session |

### 💬 Prompts (3)

| Prompt | Description |
|--------|-------------|
| `publish_product` | Guided workflow for publishing a product to KDP + Etsy + Gumroad |
| `platform_health_check` | Full audit with re-harvest plan |
| `harvest_all_platforms` | Bootstrap all platforms from scratch |

---

## Installation

### Option 1: Install from source with MCP extra (recommended)

```bash
git clone https://github.com/tenlifejosh/agentreach
cd agentreach
pip install -e ".[mcp]"
```

### Option 2: Install MCP into an existing AgentReach environment

```bash
# From your AgentReach repo directory:
pip install "agentreach[mcp]"

# Or manually add just the mcp package:
pip install mcp>=1.0.0
```

### Verify installation

```bash
# Should print the help for the MCP server entry point:
agentreach-mcp --help

# Or run directly:
python -m agentreach.mcp_server
```

---

## Claude Desktop

### Step 1: Find your config file

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Step 2: Add AgentReach to mcpServers

```json
{
  "mcpServers": {
    "agentreach": {
      "command": "agentreach-mcp",
      "env": {}
    }
  }
}
```

If `agentreach-mcp` isn't on your PATH, use the full path:

```json
{
  "mcpServers": {
    "agentreach": {
      "command": "/usr/local/bin/agentreach-mcp"
    }
  }
}
```

Or point directly at the Python module:

```json
{
  "mcpServers": {
    "agentreach": {
      "command": "python",
      "args": ["-m", "agentreach.mcp_server"]
    }
  }
}
```

### Step 3: Restart Claude Desktop

Quit and relaunch Claude Desktop. You should see AgentReach tools in the tool picker (🔧 icon).

---

## Cursor

### Step 1: Open Settings → MCP

In Cursor, go to **Settings** (`Cmd+,`) → search for **MCP** → click **Edit in settings.json**.

### Step 2: Add the server

```json
{
  "mcp.servers": {
    "agentreach": {
      "command": "agentreach-mcp",
      "transport": "stdio"
    }
  }
}
```

### Step 3: Enable in a project

In your Cursor workspace, you can also add a `.cursor/mcp.json` file to scope it to a project:

```json
{
  "mcpServers": {
    "agentreach": {
      "command": "agentreach-mcp"
    }
  }
}
```

Restart Cursor. AgentReach tools will appear in Cursor's AI tool list.

---

## Continue (VS Code / JetBrains)

Add to your `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "agentreach",
      "command": "agentreach-mcp",
      "transport": "stdio"
    }
  ]
}
```

---

## Zed

Add to your `~/.config/zed/settings.json`:

```json
{
  "assistant": {
    "mcp_servers": {
      "agentreach": {
        "command": "agentreach-mcp"
      }
    }
  }
}
```

---

## Generic MCP Config (any host)

The server uses **stdio transport** — standard input/output. Any MCP host that
supports stdio servers will work with:

```
command: agentreach-mcp
transport: stdio
```

---

## First-Time Setup: Harvest Your Sessions

Before any platform action will work, you need to harvest sessions (one-time per platform).

### Option A: Via MCP tool (in Claude Desktop / Cursor)

Once the MCP server is connected, ask your AI:

```
Use the harvest_session tool to harvest my KDP session.
```

The tool will open a browser window. Log in normally. Done.

### Option B: Via CLI (in a terminal)

```bash
agentreach harvest kdp
agentreach harvest etsy
agentreach harvest gumroad
agentreach harvest pinterest
agentreach harvest reddit
```

### Check everything is working

After harvesting, ask your AI:

```
Run vault_health to check all my AgentReach sessions.
```

You should see ✅ for each platform you've harvested.

---

## Usage Examples

Once sessions are harvested, you can talk to your AI naturally:

### Check session status
```
What's the status of all my AgentReach sessions?
```
→ Calls `vault_status`

### Publish a book to KDP
```
Use AgentReach to create a new KDP paperback:
- Title: "Pray Bold: 30-Day Journal"
- Manuscript: /path/to/interior.pdf
- Cover: /path/to/cover.pdf
- Price: $12.99
- Keywords: prayer journal, faith, Christian living
```
→ Calls `platform_action(platform="kdp", action="create_paperback", params={...})`

### Post a Pinterest pin
```
Post a Pinterest pin with image /path/to/pin.jpg, 
title "Faith Journal for Moms", 
link https://amazon.com/dp/XXXXX,
on the "Faith Journals" board.
```
→ Calls `platform_action(platform="pinterest", action="create_pin", params={...})`

### Check your KDP bookshelf
```
List all my books on KDP with their current status.
```
→ Calls `platform_action(platform="kdp", action="get_bookshelf")`

### Post to Reddit
```
Post to r/Journaling: title "New faith journal template — free this week", 
body "Just released a 30-day prayer journal template..."
```
→ Calls `platform_action(platform="reddit", action="post", params={...})`

---

## Troubleshooting

### Server not appearing in Claude Desktop / Cursor

1. Check the config file path is correct for your OS
2. Ensure `agentreach-mcp` is on your PATH: `which agentreach-mcp`
3. Check the JSON is valid (no trailing commas)
4. Fully restart the host (not just reload)

### `agentreach-mcp: command not found`

The entry point wasn't installed. Use the full path or module form:

```json
{
  "mcpServers": {
    "agentreach": {
      "command": "python",
      "args": ["-m", "agentreach.mcp_server"]
    }
  }
}
```

Or reinstall:

```bash
pip install -e ".[mcp]"
```

### Harvest fails: "No display available"

Session harvesting requires a visible desktop (it opens a real browser window).

- On macOS / Windows / Linux desktop: works out of the box
- On headless servers: use `DISPLAY=:99 Xvfb :99 &` before harvesting, or harvest
  locally and copy `~/.agentreach/vault/` to the server

### Session expired mid-operation

Re-harvest the platform:

```bash
agentreach harvest kdp   # or whichever platform
```

Or ask your AI: `Use harvest_session to re-harvest my KDP session.`

### KDP fails with "step-up authentication required"

KDP requires navigating to the title creation form during harvest to capture
deeper auth cookies. When harvesting KDP:

1. Log in normally at kdp.amazon.com
2. After the bookshelf loads, click **+ Create a new title → Paperback**
3. Wait for the Book Details form to fully load
4. AgentReach will detect this and close the browser automatically

---

## Security Notes

- Sessions are stored at `~/.agentreach/vault/` — AES-256 encrypted
- Encryption key is derived from your machine UUID — vaults are non-portable by design
- **Nothing ever leaves your machine** — no cloud sync, no telemetry
- The vault directory is gitignored by default
- The MCP server has read/write access to your vault — treat it like any local tool

---

## Architecture

```
AgentReach MCP Server
│
├── mcp_server.py          ← This file — FastMCP server with 6 tools
│
├── vault/
│   ├── store.py           ← SessionVault (AES-128-CBC Fernet encrypted storage)
│   └── health.py          ← Session health checks / expiry detection
│
├── browser/
│   ├── harvester.py       ← Visible-browser login capture
│   └── session.py         ← Headless session loader
│
└── drivers/               ← Platform-specific action drivers
    ├── kdp.py
    ├── etsy.py
    ├── gumroad.py
    ├── pinterest.py
    ├── reddit.py
    ├── twitter.py
    └── nextdoor.py
```

---

## Adding a Custom Platform Driver

1. Subclass `BasePlatformDriver` in `src/agentreach/drivers/<platform>.py`
2. Implement `platform_name`, `verify_session()`, and your action methods
3. Register in `drivers/__init__.py` → `DRIVERS` dict
4. Add capability docs to `mcp_server.py` → `DRIVER_CAPABILITIES` dict

The new platform will automatically appear in `driver_list` and become
accessible via `platform_action`.

---

*AgentReach MCP Server — part of the [Ten Life Creatives](https://tenlifecreatives.com) open-source AI toolkit.*
*MIT License © Joshua Noreen*

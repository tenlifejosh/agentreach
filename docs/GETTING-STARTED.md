# Getting Started with AgentReach

## What is AgentReach?

AgentReach gives AI agents persistent, authenticated access to web platforms like Amazon KDP, Etsy, Gumroad, and Pinterest. You log in once through a real browser window — AgentReach saves your encrypted session — and then your agent can operate those platforms headlessly, without any human in the loop.

In short: it solves the authentication wall that every AI agent hits. One 10-minute bootstrap. Autonomous forever after.

---

## Prerequisites

- Python 3.10 or later
- `pip` (comes with Python)
- A browser (Chromium will be auto-installed by Playwright)
- Accounts on the platforms you want to automate (KDP, Etsy, Gumroad, Pinterest)

That's it. No API keys required for most platforms — AgentReach uses your real login session.

---

## Install in 2 Minutes

### Step 1: Install AgentReach

```bash
pip install agentreach
```

Or from source (latest development version):

```bash
git clone https://github.com/tenlifejosh/agentreach
cd agentreach
pip install -e .
```

### Step 2: Install the browser engine

```bash
playwright install chromium
```

This downloads a ~130MB Chromium binary. One-time setup.

### Step 3: Verify it works

```bash
agentreach --version
agentreach status
```

You should see version info and a "no sessions harvested yet" message. You're ready.

---

## Harvest Your First Session

"Harvesting" means: open a real browser, log in normally, and let AgentReach save your session. You'll do this once per platform.

### Example: Harvest a Gumroad session

```bash
agentreach harvest gumroad
```

What happens:
1. A real Chrome window opens (visible, not headless)
2. You see the Gumroad login page
3. Log in exactly as you normally would — use 2FA, SSO, whatever
4. Once you're logged in and on the dashboard, type `done` in the terminal
5. AgentReach captures and encrypts your session
6. The browser closes

That's it. Your session is saved at `~/.agentreach/vault/` (AES-256 encrypted).

### Harvest other platforms

```bash
agentreach harvest kdp
agentreach harvest etsy
agentreach harvest pinterest
```

Same process for each. Budget 10 minutes total if you're doing all four.

### Check your session health

```bash
agentreach status
```

Output:
```
KDP        ✅ healthy  (expires ~23 days)
Etsy       ✅ healthy  (expires ~45 days)
Gumroad    ✅ healthy  (expires ~30 days)
Pinterest  ✅ healthy  (expires ~60 days)
```

---

## Use It in a Script

Now you can automate platform actions without any human involvement.

### Upload a book to KDP

```python
import subprocess

result = subprocess.run([
    "agentreach", "kdp", "upload",
    "--manuscript", "./interior.pdf",
    "--cover", "./cover.pdf",
    "--title", "My Book",
    "--description", "A compelling description",
    "--price", "9.99",
    "--keywords", "journal,faith,devotional"
], capture_output=True, text=True)

print(result.stdout)
```

### Check Gumroad sales

```python
import subprocess, json

result = subprocess.run(
    ["agentreach", "gumroad", "sales", "--days", "7"],
    capture_output=True, text=True
)
sales_data = json.loads(result.stdout)
print(f"Last 7 days: ${sales_data['total_revenue']:.2f}")
```

### Post to Pinterest

```python
import subprocess

subprocess.run([
    "agentreach", "pinterest", "post",
    "--image", "./pin.jpg",
    "--title", "Daily Scripture",
    "--description", "A verse for today",
    "--link", "https://gumroad.com/l/yourproduct",
    "--board", "Faith Content"
])
```

### Full CLI reference

```bash
agentreach --help
agentreach kdp --help
agentreach etsy --help
agentreach gumroad --help
agentreach pinterest --help
```

---

## Common Issues

### "Session expired" or authentication errors

Your session cookie has expired. Re-harvest it:

```bash
agentreach harvest [platform]
```

Most sessions last 30–90 days. Run `agentreach status` weekly to stay ahead of expirations.

### "Playwright browser not found"

```bash
playwright install chromium
```

If you're in a virtual environment, make sure you installed AgentReach inside it.

### "React file uploader not responding"

This is a known issue on some platform versions. AgentReach includes a React bypass engine, but sometimes platforms update their upload components.

Check for an AgentReach update first:
```bash
pip install --upgrade agentreach
```

If still failing, open a GitHub issue with the platform name and error output.

### "Permission denied" on vault directory

```bash
chmod 700 ~/.agentreach/vault/
```

### Two-factor authentication (2FA) during harvest

This works fine — just complete 2FA normally during the harvest browser session. AgentReach saves the resulting authenticated session, so 2FA won't be needed again until the session expires.

### Platform shows CAPTCHA during headless operation

Some platforms detect headless browsers. AgentReach uses anti-detection techniques, but this can still happen. Options:
1. Re-harvest (creates a fresher session)
2. Open a GitHub issue — we'll investigate and patch the driver

---

## Using with OpenClaw

Drop the AgentReach skill into your OpenClaw workspace:

```bash
# From your OpenClaw workspace directory
cp -r path/to/agentreach/skills/agentreach ./skills/
```

Then in your agent context, you can say:
> "Upload interior.pdf and cover.pdf to KDP with title 'Pray Bold'"

And the agent will invoke AgentReach automatically. No CLI required.

---

## Next Steps

- [COMMERCIAL.md](../COMMERCIAL.md) — Pro and Enterprise features
- [GitHub Issues](https://github.com/tenlifejosh/agentreach/issues) — Bug reports and feature requests
- [OpenClaw Discord](https://discord.gg/openclaw) — Community support

---

*Questions? Open an issue or email josh@tenlifecreatives.com*

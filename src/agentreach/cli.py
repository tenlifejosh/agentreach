"""
AgentReach CLI
Simple, powerful command-line interface for agent-driven platform automation.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from pathlib import Path
from typing import Optional
import sys

app = typer.Typer(
    name="agentreach",
    help="🦾 Never ask a human to open a browser again.",
    add_completion=False,
)

console = Console()

# Sub-apps for each platform
kdp_app = typer.Typer(help="Amazon KDP commands")
etsy_app = typer.Typer(help="Etsy commands")
gumroad_app = typer.Typer(help="Gumroad commands")
pinterest_app = typer.Typer(help="Pinterest commands")
reddit_app = typer.Typer(help="Reddit commands")
twitter_app = typer.Typer(help="X/Twitter commands")

app.add_typer(kdp_app, name="kdp")
app.add_typer(etsy_app, name="etsy")
app.add_typer(gumroad_app, name="gumroad")
app.add_typer(pinterest_app, name="pinterest")
app.add_typer(reddit_app, name="reddit")
app.add_typer(twitter_app, name="twitter")


# Platform metadata for display
PLATFORM_META = {
    "kdp":       {"icon": "📚", "label": "Amazon KDP"},
    "etsy":      {"icon": "🛍️", "label": "Etsy"},
    "gumroad":   {"icon": "📦", "label": "Gumroad"},
    "pinterest": {"icon": "📌", "label": "Pinterest"},
    "reddit":    {"icon": "🤖", "label": "Reddit"},
    "twitter":   {"icon": "🐦", "label": "X / Twitter"},
}


# ── Top-level commands ────────────────────────────────────────────────────────

@app.command()
def version():
    """Show AgentReach version."""
    from agentreach import __version__
    console.print(f"[bold cyan]AgentReach[/bold cyan] v{__version__}")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    ver: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
):
    if ver:
        from agentreach import __version__
        console.print(f"[bold cyan]AgentReach[/bold cyan] v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command()
def status():
    """Check health of all platform sessions (Rich table)."""
    from .vault.health import check_all, SessionStatus, PLATFORM_TTL_DAYS
    from .vault.store import SessionVault

    vault = SessionVault()
    results = check_all(vault)

    table = Table(title="🦾 AgentReach — Session Status", show_header=True, header_style="bold magenta")
    table.add_column("", width=3)           # icon
    table.add_column("Platform", style="bold", min_width=14)
    table.add_column("Status", min_width=12)
    table.add_column("Days Left", justify="right", min_width=9)
    table.add_column("Last Harvested", min_width=18)

    status_counts = {"healthy": 0, "warning": 0, "critical": 0, "expired": 0, "missing": 0}

    for h in results:
        meta = PLATFORM_META.get(h.platform, {"icon": "🔲", "label": h.platform.capitalize()})
        icon = meta["icon"]
        label = meta["label"]

        if h.status == SessionStatus.HEALTHY:
            status_text = Text("● Healthy", style="green")
            status_counts["healthy"] += 1
        elif h.status == SessionStatus.EXPIRING_SOON:
            days = h.days_remaining or 0
            if days <= 2:
                status_text = Text("● Critical", style="bold red")
                status_counts["critical"] += 1
            else:
                status_text = Text("● Warning", style="yellow")
                status_counts["warning"] += 1
        elif h.status == SessionStatus.EXPIRED:
            status_text = Text("● Expired", style="bold red")
            status_counts["expired"] += 1
        elif h.status == SessionStatus.MISSING:
            status_text = Text("○ Missing", style="dim")
            status_counts["missing"] += 1
        else:
            status_text = Text("? Unknown", style="dim")

        days_left = str(h.days_remaining) if h.days_remaining is not None else "—"
        if h.days_remaining is not None:
            if h.days_remaining <= 2:
                days_left = f"[bold red]{days_left}[/bold red]"
            elif h.days_remaining <= 5:
                days_left = f"[yellow]{days_left}[/yellow]"
            else:
                days_left = f"[green]{days_left}[/green]"

        harvested = "—"
        if h.harvested_at:
            harvested = h.harvested_at.strftime("%Y-%m-%d %H:%M")

        table.add_row(icon, label, status_text, days_left, harvested)

    console.print(table)

    # Summary line
    parts = []
    if status_counts["healthy"]:
        parts.append(f"[green]{status_counts['healthy']} healthy[/green]")
    if status_counts["warning"]:
        parts.append(f"[yellow]{status_counts['warning']} warning[/yellow]")
    if status_counts["critical"]:
        parts.append(f"[bold red]{status_counts['critical']} critical[/bold red]")
    if status_counts["expired"]:
        parts.append(f"[bold red]{status_counts['expired']} expired[/bold red]")
    if status_counts["missing"]:
        parts.append(f"[dim]{status_counts['missing']} missing[/dim]")

    summary = "  ".join(parts) if parts else "[dim]No sessions[/dim]"
    console.print(f"\n  {summary}\n")


@app.command()
def doctor():
    """Full system health check — sessions, drivers, vault, recommendations."""
    import subprocess
    from .vault.health import check_all, SessionStatus, PLATFORM_TTL_DAYS
    from .vault.store import SessionVault
    from agentreach import __version__

    console.rule("[bold cyan]🦾 AgentReach Doctor[/bold cyan]")
    console.print()

    # ── 1. Version ────────────────────────────────────────────────────────────
    console.print(f"[bold]Version:[/bold] AgentReach v{__version__}")

    # ── 2. Python version ─────────────────────────────────────────────────────
    import platform as _platform
    py_ver = _platform.python_version()
    console.print(f"[bold]Python:[/bold]  {py_ver}")
    console.print()

    # ── 3. Sessions table ─────────────────────────────────────────────────────
    vault = SessionVault()
    results = check_all(vault)

    console.rule("[bold]Sessions[/bold]")
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Platform", min_width=14)
    table.add_column("Status", min_width=14)
    table.add_column("Days Left", justify="right", min_width=9)
    table.add_column("Harvested", min_width=18)
    table.add_column("Action Needed", min_width=40)

    recommendations = []
    for h in results:
        meta = PLATFORM_META.get(h.platform, {"icon": "🔲", "label": h.platform.capitalize()})
        label = f"{meta['icon']}  {meta['label']}"

        if h.status == SessionStatus.HEALTHY:
            s = Text("✅ Healthy", style="green")
            action = Text("None", style="dim")
        elif h.status == SessionStatus.EXPIRING_SOON:
            days = h.days_remaining or 0
            if days <= 2:
                s = Text("🔴 Critical", style="bold red")
                action = Text(f"agentreach harvest {h.platform}", style="bold red")
                recommendations.append((h.platform, "critical", days))
            else:
                s = Text("⚠️  Warning", style="yellow")
                action = Text(f"agentreach harvest {h.platform}", style="yellow")
                recommendations.append((h.platform, "warning", days))
        elif h.status == SessionStatus.EXPIRED:
            s = Text("❌ Expired", style="bold red")
            action = Text(f"agentreach harvest {h.platform}", style="bold red")
            recommendations.append((h.platform, "expired", None))
        elif h.status == SessionStatus.MISSING:
            s = Text("○ Missing", style="dim")
            action = Text(f"agentreach harvest {h.platform}", style="dim")
        else:
            s = Text("? Unknown", style="dim")
            action = Text("Check manually", style="dim")

        days_left = str(h.days_remaining) if h.days_remaining is not None else "—"
        harvested = h.harvested_at.strftime("%Y-%m-%d %H:%M") if h.harvested_at else "—"

        table.add_row(label, s, days_left, harvested, action)

    console.print(table)
    console.print()

    # ── 4. Driver versions ────────────────────────────────────────────────────
    console.rule("[bold]Driver Versions[/bold]")
    driver_table = Table(show_header=True, header_style="bold blue")
    driver_table.add_column("Driver", min_width=14)
    driver_table.add_column("Status", min_width=12)

    driver_names = ["kdp", "etsy", "gumroad", "pinterest", "reddit", "twitter"]
    for name in driver_names:
        meta = PLATFORM_META.get(name, {"icon": "🔲", "label": name.capitalize()})
        label = f"{meta['icon']}  {meta['label']}"
        try:
            from .drivers import get_driver
            _ = get_driver(name)
            driver_table.add_row(label, Text("✅ Loaded", style="green"))
        except Exception as e:
            driver_table.add_row(label, Text(f"❌ {e}", style="red"))

    console.print(driver_table)
    console.print()

    # ── 5. Vault status ───────────────────────────────────────────────────────
    console.rule("[bold]Vault[/bold]")
    from .vault.store import VAULT_DIR
    vault_path = VAULT_DIR
    vault_exists = vault_path.exists()
    vault_files = list(vault_path.glob("*.vault")) if vault_exists else []

    console.print(f"  Path:    [cyan]{vault_path}[/cyan]")
    console.print(f"  Exists:  {'[green]Yes[/green]' if vault_exists else '[red]No[/red]'}")
    console.print(f"  Sessions stored: [bold]{len(vault_files)}[/bold]")
    console.print()

    # ── 6. Playwright ─────────────────────────────────────────────────────────
    console.rule("[bold]Browser (Playwright)[/bold]")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import playwright; print(playwright.__version__)"],
            capture_output=True, text=True, timeout=10
        )
        pw_ver = result.stdout.strip() or "installed"
        console.print(f"  Playwright: [green]{pw_ver}[/green]")
    except Exception:
        console.print("  Playwright: [red]not found — run: playwright install[/red]")

    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run"],
            capture_output=True, text=True, timeout=10
        )
        console.print(f"  Chromium: [green]available[/green]")
    except Exception:
        console.print("  Chromium: [yellow]status unknown[/yellow]")

    console.print()

    # ── 7. Recommendations ────────────────────────────────────────────────────
    if recommendations:
        console.rule("[bold yellow]Recommendations[/bold yellow]")
        for platform, severity, days in recommendations:
            if severity == "expired":
                console.print(f"  [bold red]❌  {platform.upper()}[/bold red] session expired — re-harvest immediately:")
                console.print(f"      [yellow]agentreach harvest {platform}[/yellow]")
            elif severity == "critical":
                console.print(f"  [red]🔴  {platform.upper()}[/red] expires in {days} days — harvest soon:")
                console.print(f"      [yellow]agentreach harvest {platform}[/yellow]")
            elif severity == "warning":
                console.print(f"  [yellow]⚠️   {platform.upper()}[/yellow] expires in {days} days — schedule re-harvest:")
                console.print(f"      [dim]agentreach harvest {platform}[/dim]")
        console.print()
    else:
        console.print("[green]✅  All sessions healthy — no action required.[/green]\n")

    console.rule("[bold cyan]Doctor complete[/bold cyan]")


@app.command()
def platforms():
    """List all supported platforms with session status."""
    from .vault.health import check_session, SessionStatus
    from .vault.store import SessionVault

    vault = SessionVault()

    table = Table(title="🦾 AgentReach — Supported Platforms", show_header=True, header_style="bold magenta")
    table.add_column("", width=3)
    table.add_column("Platform", style="bold", min_width=14)
    table.add_column("Session", min_width=12)
    table.add_column("Auth Method", min_width=20)
    table.add_column("Bootstrap Command", min_width=30)

    PLATFORM_AUTH = {
        "kdp":       "Browser (cookie harvest)",
        "etsy":      "API token + OAuth",
        "gumroad":   "API token",
        "pinterest": "Browser (cookie harvest)",
        "reddit":    "Browser (cookie harvest)",
        "twitter":   "Browser (cookie harvest)",
    }

    for platform, meta in PLATFORM_META.items():
        health = check_session(platform, vault)
        if health.status == SessionStatus.HEALTHY:
            session_text = Text("● Active", style="green")
        elif health.status == SessionStatus.EXPIRING_SOON:
            session_text = Text("● Expiring", style="yellow")
        elif health.status == SessionStatus.EXPIRED:
            session_text = Text("● Expired", style="red")
        else:
            session_text = Text("○ None", style="dim")

        auth = PLATFORM_AUTH.get(platform, "Unknown")
        cmd = f"agentreach harvest {platform}"

        table.add_row(meta["icon"], meta["label"], session_text, auth, f"[dim]{cmd}[/dim]")

    console.print(table)


@app.command()
def backup(
    output: Optional[Path] = typer.Option(None, help="Output file path (default: ~/.agentreach/backups/vault-YYYY-MM-DD.enc)"),
):
    """Export encrypted vault to a backup file."""
    import shutil
    from datetime import date
    from .vault.store import VAULT_DIR

    backup_dir = Path.home() / ".agentreach" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if output is None:
        today = date.today().strftime("%Y-%m-%d")
        output = backup_dir / f"vault-{today}.enc"

    vault_files = list(VAULT_DIR.glob("*.vault"))
    if not vault_files:
        console.print("[yellow]⚠️  No vault sessions found. Nothing to backup.[/yellow]")
        raise typer.Exit(0)

    # Pack all vault files into a single encrypted archive
    import json
    import base64
    from cryptography.fernet import Fernet
    from .vault.store import _FERNET

    bundle = {}
    for vf in vault_files:
        raw = vf.read_bytes()
        bundle[vf.name] = base64.b64encode(raw).decode()

    payload = json.dumps(bundle).encode()
    encrypted = _FERNET.encrypt(payload)
    output.write_bytes(encrypted)

    console.print(f"[green]✅ Vault backed up:[/green] {output}")
    console.print(f"   Sessions included: {', '.join(vf.stem for vf in vault_files)}")
    console.print(f"   Size: {len(encrypted):,} bytes")


@app.command()
def restore(
    input_file: Path = typer.Argument(..., help="Backup file to restore from (.enc)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing sessions"),
):
    """Import vault sessions from a backup file."""
    import json
    import base64
    from .vault.store import VAULT_DIR, _FERNET

    if not input_file.exists():
        console.print(f"[red]❌ File not found: {input_file}[/red]")
        raise typer.Exit(1)

    try:
        encrypted = input_file.read_bytes()
        payload = _FERNET.decrypt(encrypted)
        bundle = json.loads(payload.decode())
    except Exception as e:
        console.print(f"[red]❌ Failed to decrypt backup: {e}[/red]")
        raise typer.Exit(1)

    restored = []
    skipped = []

    for filename, encoded in bundle.items():
        dest = VAULT_DIR / filename
        if dest.exists() and not overwrite:
            skipped.append(filename)
            continue
        raw = base64.b64decode(encoded)
        dest.write_bytes(raw)
        restored.append(filename)

    if restored:
        console.print(f"[green]✅ Restored:[/green] {', '.join(r.replace('.vault','') for r in restored)}")
    if skipped:
        console.print(f"[yellow]⏭  Skipped (already exist):[/yellow] {', '.join(s.replace('.vault','') for s in skipped)}")
        console.print("   Use --overwrite to replace existing sessions.")

    if not restored and not skipped:
        console.print("[dim]No sessions in backup file.[/dim]")


@app.command()
def harvest(
    platform: str = typer.Argument(..., help="Platform to harvest: kdp, etsy, gumroad, pinterest, reddit, twitter"),
    timeout: int = typer.Option(300, help="Seconds to wait for login (default: 300)"),
):
    """
    Bootstrap a platform session. Opens a browser — log in normally.
    This is the ONE-TIME setup per platform. After this: fully autonomous.
    """
    from .browser.harvester import harvest as do_harvest
    do_harvest(platform, timeout=timeout)


@app.command()
def verify(
    platform: str = typer.Argument(..., help="Platform to verify"),
):
    """Verify a saved session is still valid (makes a live request)."""
    from .drivers import get_driver
    driver = get_driver(platform)
    import asyncio
    valid = asyncio.run(driver.verify_session())
    if valid:
        rprint(f"[green]✅ {platform.upper()} session is valid.[/green]")
    else:
        rprint(f"[red]❌ {platform.upper()} session is invalid or expired. Run: agentreach harvest {platform}[/red]")


# ── KDP commands ──────────────────────────────────────────────────────────────

@kdp_app.command("upload")
def kdp_upload(
    manuscript: Path = typer.Option(..., help="Path to interior PDF"),
    cover: Path = typer.Option(..., help="Path to cover PDF (full wrap)"),
    title: str = typer.Option(..., help="Book title"),
    subtitle: str = typer.Option("", help="Book subtitle"),
    author: str = typer.Option("Joshua Noreen", help="Author name"),
    description: str = typer.Option("", help="HTML book description"),
    price: float = typer.Option(12.99, help="USD price"),
    keywords: str = typer.Option("", help="Comma-separated keywords (up to 7)"),
):
    """Upload a new paperback to Amazon KDP."""
    from .drivers.kdp import KDPDriver, KDPBookDetails

    details = KDPBookDetails(
        title=title,
        subtitle=subtitle,
        author=author,
        description=description,
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        price_usd=price,
    )

    console.print(f"[bold]📚 Uploading '{title}' to KDP...[/bold]")
    driver = KDPDriver()
    driver.require_valid_session()
    result = driver.upload_paperback(details, manuscript, cover)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
        if result.product_id:
            rprint(f"   KDP ID: {result.product_id}")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


@kdp_app.command("bookshelf")
def kdp_bookshelf():
    """List all books on your KDP bookshelf with current status."""
    import asyncio
    from .drivers.kdp import KDPDriver

    driver = KDPDriver()
    driver.require_valid_session()
    books = asyncio.run(driver.get_bookshelf())

    table = Table(title="KDP Bookshelf")
    table.add_column("Title", style="cyan")
    table.add_column("Status", style="green")

    for book in books:
        table.add_row(book["title"], book["status"])

    console.print(table)


# ── Gumroad commands ──────────────────────────────────────────────────────────

@gumroad_app.command("set-token")
def gumroad_set_token(
    token: str = typer.Argument(..., help="Gumroad API access token"),
):
    """Save a Gumroad API access token to the vault."""
    from .drivers.gumroad import GumroadDriver
    driver = GumroadDriver()
    driver.save_token(token)


@gumroad_app.command("publish")
def gumroad_publish(
    name: str = typer.Option(..., help="Product name"),
    description: str = typer.Option(..., help="Product description"),
    price: float = typer.Option(..., help="Price in USD (e.g. 7.99)"),
    file: Optional[Path] = typer.Option(None, help="Path to digital file (PDF, ZIP, etc.)"),
    url: str = typer.Option("", help="Custom URL slug"),
):
    """Publish a new product to Gumroad."""
    from .drivers.gumroad import GumroadDriver, GumroadProduct

    product = GumroadProduct(
        name=name,
        description=description,
        price_cents=int(price * 100),
        file_path=str(file) if file else None,
        custom_url=url,
    )

    console.print(f"[bold]📦 Publishing '{name}' to Gumroad...[/bold]")
    driver = GumroadDriver()
    driver.require_valid_session()
    result = driver.publish_product(product)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
        rprint(f"   URL: {result.url}")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


@gumroad_app.command("sales")
def gumroad_sales(
    after: Optional[str] = typer.Option(None, help="ISO date to filter from (e.g. 2026-01-01)"),
):
    """Check Gumroad sales."""
    from .drivers.gumroad import GumroadDriver
    driver = GumroadDriver()
    data = driver.check_sales(after=after)
    sales = data.get("sales", [])
    rprint(f"[bold]Total sales found: {len(sales)}[/bold]")
    for s in sales[:10]:
        rprint(f"  ${s.get('price', 0)/100:.2f} — {s.get('product_name', 'Unknown')} — {s.get('created_at', '')}")


# ── Etsy commands ─────────────────────────────────────────────────────────────

@etsy_app.command("set-credentials")
def etsy_set_credentials(
    api_key: str = typer.Option(..., help="Etsy API key"),
    access_token: str = typer.Option(..., help="OAuth access token"),
    shop_id: str = typer.Option(..., help="Your Etsy shop ID"),
):
    """Save Etsy API credentials to the vault."""
    from .drivers.etsy import EtsyDriver
    driver = EtsyDriver()
    driver.save_credentials(api_key, access_token, shop_id)


@etsy_app.command("publish")
def etsy_publish(
    title: str = typer.Option(..., help="Listing title"),
    description: str = typer.Option(..., help="Listing description"),
    price: float = typer.Option(..., help="Price in USD"),
    digital_file: Optional[Path] = typer.Option(None, help="Path to digital file"),
    images: str = typer.Option("", help="Comma-separated paths to mockup images"),
    tags: str = typer.Option("", help="Comma-separated tags (up to 13)"),
):
    """Publish a new listing to Etsy."""
    from .drivers.etsy import EtsyDriver, EtsyListing

    listing = EtsyListing(
        title=title,
        description=description,
        price=price,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        digital_files=[str(digital_file)] if digital_file else [],
        image_paths=[i.strip() for i in images.split(",") if i.strip()],
    )

    console.print(f"[bold]🛍️  Publishing '{title}' to Etsy...[/bold]")
    driver = EtsyDriver()
    driver.require_valid_session()
    result = driver.publish_listing(listing)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


# ── Pinterest commands ────────────────────────────────────────────────────────

@pinterest_app.command("pin")
def pinterest_pin(
    title: str = typer.Option(..., help="Pin title"),
    description: str = typer.Option(..., help="Pin description"),
    image: Path = typer.Option(..., help="Path to pin image"),
    link: str = typer.Option("", help="Destination URL"),
    board: str = typer.Option("Faith Journals", help="Board name"),
):
    """Post a new pin to Pinterest."""
    from .drivers.pinterest import PinterestDriver, PinterestPin

    pin = PinterestPin(
        title=title,
        description=description,
        image_path=image,
        link=link,
        board_name=board,
    )

    console.print(f"[bold]📌 Posting pin '{title}' to Pinterest...[/bold]")
    driver = PinterestDriver()
    driver.require_valid_session()
    result = driver.post_pin(pin)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


# ── Reddit commands ───────────────────────────────────────────────────────────

@reddit_app.command("comment")
def reddit_comment(
    url: str = typer.Argument(..., help="Full URL of the Reddit thread"),
    text: str = typer.Argument(..., help="Comment text to post"),
):
    """Post a comment on a Reddit thread."""
    from .drivers.reddit import RedditDriver

    console.print(f"[bold]💬 Posting comment on Reddit...[/bold]")
    driver = RedditDriver()
    driver.require_valid_session()
    result = driver.comment(url, text)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


@reddit_app.command("post")
def reddit_post(
    subreddit: str = typer.Argument(..., help="Subreddit name (without r/ prefix)"),
    title: str = typer.Argument(..., help="Post title"),
    body: str = typer.Argument(..., help="Post body text"),
):
    """Create a new text post in a subreddit."""
    from .drivers.reddit import RedditDriver

    console.print(f"[bold]📝 Creating post in r/{subreddit}...[/bold]")
    driver = RedditDriver()
    driver.require_valid_session()
    result = driver.post(subreddit, title, body)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
        if result.url:
            rprint(f"   URL: {result.url}")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


# ── Twitter/X commands ────────────────────────────────────────────────────────

@twitter_app.command("tweet")
def twitter_tweet(
    text: str = typer.Argument(..., help="Tweet text (max 280 characters)"),
):
    """Post a new tweet to X/Twitter."""
    from .drivers.twitter import TwitterDriver

    console.print(f"[bold]🐦 Posting tweet...[/bold]")
    driver = TwitterDriver()
    driver.require_valid_session()
    result = driver.tweet(text)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


@twitter_app.command("reply")
def twitter_reply(
    url: str = typer.Argument(..., help="Full URL to the tweet to reply to"),
    text: str = typer.Argument(..., help="Reply text"),
):
    """Reply to a tweet by URL."""
    from .drivers.twitter import TwitterDriver

    console.print(f"[bold]↩️  Posting reply...[/bold]")
    driver = TwitterDriver()
    driver.require_valid_session()
    result = driver.reply(url, text)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()

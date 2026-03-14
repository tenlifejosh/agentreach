"""
AgentReach CLI
Simple, powerful command-line interface for agent-driven platform automation.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from pathlib import Path
from typing import Optional

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

app.add_typer(kdp_app, name="kdp")
app.add_typer(etsy_app, name="etsy")
app.add_typer(gumroad_app, name="gumroad")
app.add_typer(pinterest_app, name="pinterest")


# ── Top-level commands ────────────────────────────────────────────────────────

@app.command()
def status():
    """Check health of all platform sessions."""
    from .vault.health import status_report
    report = status_report()
    console.print(report)


@app.command()
def harvest(
    platform: str = typer.Argument(..., help="Platform to harvest: kdp, etsy, gumroad, pinterest"),
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
        url=url,
    )

    console.print(f"[bold]📦 Publishing '{name}' to Gumroad...[/bold]")
    driver = GumroadDriver()
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
    result = driver.post_pin(pin)

    if result.success:
        rprint(f"[green]✅ {result.message}[/green]")
    else:
        rprint(f"[red]❌ {result.error}[/red]")
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()

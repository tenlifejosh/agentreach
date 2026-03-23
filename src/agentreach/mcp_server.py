"""
AgentReach MCP Server
=====================
Exposes AgentReach capabilities — encrypted session vault, headless platform
drivers — as MCP (Model Context Protocol) tools.

Supports: Claude Desktop, Cursor, Continue, Zed, and any MCP-compatible host.

Run directly:
    python -m agentreach.mcp_server

Or via the installed entry-point:
    agentreach-mcp

Configure in Claude Desktop / Cursor:
    See docs/MCP_SETUP.md for full instructions.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP, Context

# ── AgentReach imports (vault + drivers) ──────────────────────────────────────
from agentreach.vault.store import SessionVault
from agentreach.vault.health import (
    check_session,
    check_all,
    SessionStatus,
    PLATFORM_TTL_DAYS,
)
from agentreach.drivers import DRIVERS, get_driver

# ── Initialise the FastMCP server ─────────────────────────────────────────────
mcp = FastMCP(
    name="agentreach",
    instructions=(
        "AgentReach gives AI agents persistent, authenticated access to web platforms "
        "(KDP, Etsy, Gumroad, Pinterest, Reddit, Nextdoor, Twitter/X). "
        "Sessions are AES-128-CBC (Fernet) encrypted and stored locally — nothing leaves the machine. "
        "Use vault_status / vault_health to inspect stored sessions, platform_login to "
        "verify a session is active, harvest_session to guide the human through "
        "authenticating a new platform, driver_list to discover available drivers and "
        "their actions, and platform_action to execute real platform operations."
    ),
)

# Module-level vault (shared across all tool calls in a process)
_vault = SessionVault()


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _health_to_dict(h) -> dict[str, Any]:
    """Convert SessionHealth dataclass to a JSON-serialisable dict."""
    return {
        "platform": h.platform,
        "status": h.status.value,
        "harvested_at": h.harvested_at.isoformat() if h.harvested_at else None,
        "estimated_expiry": h.estimated_expiry.isoformat() if h.estimated_expiry else None,
        "days_remaining": h.days_remaining,
        "message": h.message,
    }


def _fmt_health_line(h) -> str:
    icons = {
        SessionStatus.HEALTHY: "✅",
        SessionStatus.EXPIRING_SOON: "⚠️ ",
        SessionStatus.EXPIRED: "❌",
        SessionStatus.MISSING: "○ ",
        SessionStatus.UNKNOWN: "? ",
    }
    icon = icons.get(h.status, "  ")
    return f"{icon} {h.platform:<14} {h.message}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: vault_status
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="vault_status",
    description=(
        "List all platforms that have stored sessions in the AgentReach vault, "
        "including their harvest timestamp and estimated expiry. "
        "Use this for a quick overview before running platform operations."
    ),
)
def vault_status() -> str:
    """
    Returns a summary of every vaulted session: platform name, harvest date,
    estimated expiry, and days remaining.
    """
    try:
        platforms_in_vault = _vault.list_platforms()

        if not platforms_in_vault:
            return (
                "🔒 AgentReach vault is empty.\n\n"
                "No sessions have been harvested yet.\n"
                "Use the harvest_session tool (or run `agentreach harvest <platform>` in a terminal) "
                "to bootstrap a platform."
            )

        # Build status for everything in vault + all known platforms
        all_known = set(PLATFORM_TTL_DAYS.keys()) | set(platforms_in_vault)
        results = [check_session(p, _vault) for p in sorted(all_known)]

        lines = [
            "🔐 AgentReach Vault Status",
            "=" * 48,
            f"Vault location: ~/.agentreach/vault/",
            f"Sessions stored: {len(platforms_in_vault)}",
            "",
        ]
        for h in results:
            lines.append(_fmt_health_line(h))

        lines += [
            "",
            "Legend: ✅ healthy  ⚠️  expiring soon  ❌ expired  ○ not harvested",
            "",
            "To refresh a session: use harvest_session tool or run:",
            "  agentreach harvest <platform>",
        ]
        return "\n".join(lines)

    except Exception as exc:
        return f"❌ vault_status error: {exc}\n{traceback.format_exc()}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: vault_health
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="vault_health",
    description=(
        "Run a comprehensive health check on all platform sessions in the vault. "
        "Returns structured data for every known platform — healthy, expiring, expired, "
        "or missing — along with days remaining and suggested remediation steps. "
        "Use this before batch operations to ensure all required sessions are fresh."
    ),
)
def vault_health(
    platforms: Optional[list[str]] = None,
) -> str:
    """
    Check health of all (or specific) platform sessions.

    Args:
        platforms: Optional list of platform names to check (e.g. ["kdp", "etsy"]).
                   Omit to check all known platforms.
    """
    try:
        if platforms:
            results = [check_session(p.lower(), _vault) for p in platforms]
        else:
            results = check_all(_vault)

        # Counts by status
        counts: dict[str, int] = {}
        for h in results:
            counts[h.status.value] = counts.get(h.status.value, 0) + 1

        lines = [
            "🏥 AgentReach Vault Health Report",
            "=" * 48,
            f"Checked: {len(results)} platform(s)",
            f"Healthy: {counts.get('healthy', 0)}  "
            f"Expiring: {counts.get('expiring_soon', 0)}  "
            f"Expired: {counts.get('expired', 0)}  "
            f"Missing: {counts.get('missing', 0)}",
            "",
        ]

        for h in results:
            lines.append(_fmt_health_line(h))
            if h.harvested_at:
                lines.append(
                    f"   {'Harvested':>12}: {h.harvested_at.strftime('%Y-%m-%d %H:%M UTC')}"
                )
            if h.estimated_expiry and h.days_remaining is not None:
                lines.append(
                    f"   {'Est. expiry':>12}: {h.estimated_expiry.strftime('%Y-%m-%d')} "
                    f"({h.days_remaining}d remaining)"
                )
            lines.append("")

        # Action items
        action_needed = [h for h in results if h.status in (SessionStatus.EXPIRED, SessionStatus.MISSING)]
        expiring_soon = [h for h in results if h.status == SessionStatus.EXPIRING_SOON]

        if action_needed:
            lines.append("⚡ ACTION REQUIRED:")
            for h in action_needed:
                lines.append(f"   agentreach harvest {h.platform}")
            lines.append("")

        if expiring_soon:
            lines.append("📅 EXPIRING SOON — refresh soon:")
            for h in expiring_soon:
                lines.append(f"   agentreach harvest {h.platform}  ({h.days_remaining}d left)")
            lines.append("")

        return "\n".join(lines)

    except Exception as exc:
        return f"❌ vault_health error: {exc}\n{traceback.format_exc()}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: platform_login
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="platform_login",
    description=(
        "Verify that AgentReach has a valid, active session for a given platform by "
        "performing a live headless browser check against the platform's logged-in URL. "
        "Returns whether the session is authenticated and ready for autonomous actions. "
        "Supported platforms: kdp, etsy, gumroad, pinterest, reddit, twitter, nextdoor."
    ),
)
async def platform_login(
    platform: str,
    ctx: Context,
) -> str:
    """
    Verify a saved session is still active by loading it in a headless browser
    and checking the post-login URL.

    Args:
        platform: Platform to verify (kdp, etsy, gumroad, pinterest, reddit, twitter, nextdoor).
    """
    platform = platform.lower().strip()

    if platform not in DRIVERS:
        available = ", ".join(sorted(DRIVERS.keys()))
        return (
            f"❌ Unknown platform: '{platform}'\n"
            f"Available platforms: {available}\n\n"
            "Use driver_list to see all available drivers."
        )

    # Quick vault check first (fast path)
    health = check_session(platform, _vault)
    if health.status == SessionStatus.MISSING:
        return (
            f"○ No session found for '{platform}'.\n\n"
            f"Use harvest_session to bootstrap this platform:\n"
            f"  harvest_session(platform='{platform}')"
        )

    await ctx.info(f"Loading {platform} driver and verifying session...")

    try:
        driver = get_driver(platform)
        is_valid = await asyncio.wait_for(driver.verify_session(), timeout=45)

        if is_valid:
            return (
                f"✅ {platform.upper()} session is ACTIVE and authenticated.\n\n"
                f"Vault status: {health.message}\n"
                f"Ready for autonomous platform_action calls."
            )
        else:
            return (
                f"❌ {platform.upper()} session is INVALID or EXPIRED.\n\n"
                f"The session file exists but the platform rejected it.\n"
                f"Re-harvest with:\n"
                f"  harvest_session(platform='{platform}')\n"
                f"or run: agentreach harvest {platform}"
            )

    except asyncio.TimeoutError:
        return (
            f"⚠️  Verification timed out for {platform.upper()} (45s limit).\n"
            "The platform may be slow or unreachable. Try again, or check your connection."
        )
    except Exception as exc:
        return (
            f"❌ platform_login error for '{platform}': {exc}\n\n"
            f"The session may be present in the vault but verification failed.\n"
            f"Consider re-harvesting: harvest_session(platform='{platform}')"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: harvest_session
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="harvest_session",
    description=(
        "Guide the user through a one-time session harvest for a platform. "
        "This opens a VISIBLE browser window so the user can log in normally. "
        "AgentReach captures and encrypts the session — the platform is then "
        "fully autonomous for ~30-60 days without any further human involvement. "
        "Run this ONCE per platform, then never log in manually again. "
        "IMPORTANT: This requires a physical display and user interaction — "
        "the agent starts the process, the human completes the login."
    ),
)
def harvest_session(
    platform: str,
    timeout_seconds: int = 300,
) -> str:
    """
    Start an interactive session harvest for a platform.

    Opens a real (non-headless) browser window. The user logs in normally.
    AgentReach captures cookies/storage state and encrypts them to the vault.

    Args:
        platform:        Platform to harvest (kdp, etsy, gumroad, pinterest, reddit, twitter, nextdoor).
        timeout_seconds: Seconds to wait for the user to complete login (default: 300 = 5 min).
    """
    platform = platform.lower().strip()

    from agentreach.browser.harvester import LOGIN_URLS, POST_LOGIN_DEEP_STEPS

    if platform not in LOGIN_URLS:
        available = ", ".join(sorted(LOGIN_URLS.keys()))
        return (
            f"❌ Unknown platform: '{platform}'\n"
            f"Harvestable platforms: {available}"
        )

    # Build human-readable instructions before kicking off
    deep = POST_LOGIN_DEEP_STEPS.get(platform)
    deep_note = ""
    if deep:
        deep_note = (
            f"\n\n⚠️  {platform.upper()} EXTRA STEP REQUIRED:\n"
            f"{deep['instructions']}"
        )

    instructions = (
        f"🌐 Starting AgentReach session harvest for: {platform.upper()}\n"
        f"{'=' * 50}\n\n"
        f"A browser window will open in a moment.\n"
        f"→ Log in to {platform.upper()} as you normally would.\n"
        f"→ AgentReach will detect when login is complete automatically.\n"
        f"→ You have {timeout_seconds // 60} minutes.\n"
        f"{deep_note}\n\n"
        f"Login URL: {LOGIN_URLS[platform]}\n\n"
        f"Starting browser now..."
    )

    try:
        from agentreach.browser.harvester import harvest
        harvest(platform, vault=_vault, timeout=timeout_seconds)

        # Verify it worked
        health = check_session(platform, _vault)
        return (
            f"{instructions}\n\n"
            f"✅ Session harvested successfully!\n\n"
            f"Platform: {platform.upper()}\n"
            f"Status:   {health.message}\n"
            f"Vault:    ~/.agentreach/vault/{platform}.vault\n\n"
            f"{platform.upper()} is now fully autonomous. "
            f"Use platform_action to run operations without any further human involvement."
        )

    except Exception as exc:
        return (
            f"{instructions}\n\n"
            f"❌ Harvest failed: {exc}\n\n"
            f"Common causes:\n"
            f"  • No display available (harvest requires a physical/virtual desktop)\n"
            f"  • Playwright not installed: playwright install chromium\n"
            f"  • Timed out before login was completed\n\n"
            f"Try again with: harvest_session(platform='{platform}', timeout_seconds=600)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: driver_list
# ─────────────────────────────────────────────────────────────────────────────

# Capability map: platform → {action: description}
DRIVER_CAPABILITIES: dict[str, dict[str, str]] = {
    "kdp": {
        "create_paperback": "Create a new KDP paperback listing (title, author, description, keywords, categories, manuscript PDF, cover PDF, price)",
        "resume_paperback": "Resume/continue an in-progress KDP paperback from a specific step (1=details, 2=content, 3=pricing)",
        "get_bookshelf": "List all books on the KDP bookshelf with their publish status",
        "verify_session": "Verify the KDP session is active and has full title-creation access",
    },
    "etsy": {
        "create_listing": "Create a new Etsy digital product listing with title, description, price, tags, and digital file uploads",
        "get_shop_sections": "List all sections in the Etsy shop",
        "get_shop_listings": "List active shop listings with IDs and pricing",
        "verify_session": "Verify the Etsy session or API credentials are valid",
    },
    "gumroad": {
        "create_product": "Create a new Gumroad digital product (name, description, price, file upload)",
        "list_products": "List all products in the Gumroad account",
        "verify_session": "Verify the Gumroad session is active",
    },
    "pinterest": {
        "create_pin": "Create a Pinterest pin (image, title, description, link, board)",
        "ensure_board_exists": "Check if a board exists; create it if not",
        "verify_session": "Verify the Pinterest session is active",
    },
    "reddit": {
        "post": "Create a new Reddit submission (subreddit, title, body text)",
        "comment": "Post a comment on a Reddit thread by URL",
        "verify_session": "Verify the Reddit session is active",
    },
    "twitter": {
        "post_tweet": "Post a tweet / X post (text, optional media)",
        "verify_session": "Verify the Twitter/X session is active",
    },
    "nextdoor": {
        "post": "Create a Nextdoor neighborhood post (title, body, category)",
        "verify_session": "Verify the Nextdoor session is active",
    },
}


@mcp.tool(
    name="driver_list",
    description=(
        "List all available AgentReach platform drivers and their supported actions. "
        "Shows each platform, its current vault status, and the specific operations "
        "that can be invoked via platform_action. Use this to discover what actions "
        "are possible before calling platform_action."
    ),
)
def driver_list(
    platform: Optional[str] = None,
) -> str:
    """
    List available platform drivers and their capabilities.

    Args:
        platform: Optional — filter to a single platform for detailed capability info.
                  Omit to list all platforms.
    """
    try:
        if platform:
            platform = platform.lower().strip()
            if platform not in DRIVERS:
                available = ", ".join(sorted(DRIVERS.keys()))
                return f"❌ Unknown platform: '{platform}'\nAvailable: {available}"

            caps = DRIVER_CAPABILITIES.get(platform, {})
            health = check_session(platform, _vault)

            lines = [
                f"🔌 {platform.upper()} Driver",
                "=" * 40,
                f"Status: {_fmt_health_line(health)}",
                "",
                "Actions:",
            ]
            if caps:
                for action, desc in caps.items():
                    lines.append(f"  • {action}")
                    lines.append(f"      {desc}")
            else:
                lines.append("  (No documented actions — check driver source)")

            lines += [
                "",
                f"Example platform_action call:",
                f'  platform_action(platform="{platform}", action="verify_session")',
            ]
            return "\n".join(lines)

        # All platforms
        lines = [
            "🔌 AgentReach Platform Drivers",
            "=" * 48,
            "",
        ]

        for p in sorted(DRIVERS.keys()):
            health = check_session(p, _vault)
            status_icon = {
                SessionStatus.HEALTHY: "✅",
                SessionStatus.EXPIRING_SOON: "⚠️ ",
                SessionStatus.EXPIRED: "❌",
                SessionStatus.MISSING: "○ ",
                SessionStatus.UNKNOWN: "? ",
            }.get(health.status, "  ")

            caps = DRIVER_CAPABILITIES.get(p, {})
            action_names = ", ".join(caps.keys()) if caps else "(see driver source)"

            lines.append(f"{status_icon} {p.upper():<14} {action_names}")

        lines += [
            "",
            "Use driver_list(platform='<name>') for detailed action descriptions.",
            "",
            "To run an action: platform_action(platform='<name>', action='<action>', params={...})",
            "",
            "To add a new platform driver:",
            "  1. Subclass BasePlatformDriver in src/agentreach/drivers/<platform>.py",
            "  2. Register it in drivers/__init__.py DRIVERS dict",
            "  3. Add capability docs to mcp_server.py DRIVER_CAPABILITIES",
        ]
        return "\n".join(lines)

    except Exception as exc:
        return f"❌ driver_list error: {exc}\n{traceback.format_exc()}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: platform_action
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="platform_action",
    description=(
        "Execute a driver action on a supported platform using the stored session. "
        "This is the primary execution tool — it dispatches to the correct platform "
        "driver and runs the requested action autonomously (no human browser needed). "
        "\n\nExamples:\n"
        "  platform_action(platform='kdp', action='get_bookshelf')\n"
        "  platform_action(platform='pinterest', action='create_pin', params={"
        "'title': 'My Pin', 'description': '...', 'image_path': '/path/to/image.jpg', "
        "'link': 'https://amazon.com/dp/...', 'board_name': 'Faith Journals'})\n"
        "  platform_action(platform='reddit', action='post', params={"
        "'subreddit': 'Journaling', 'title': 'New journal template', 'body': '...'})\n"
        "  platform_action(platform='kdp', action='create_paperback', params={...})\n"
        "\nUse driver_list to discover available actions and their parameters."
    ),
)
async def platform_action(
    platform: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> str:
    """
    Execute a platform driver action autonomously.

    Args:
        platform: Target platform (kdp, etsy, gumroad, pinterest, reddit, twitter, nextdoor).
        action:   Driver method to call (e.g. 'create_pin', 'post', 'get_bookshelf').
        params:   Dictionary of keyword arguments for the action method.
                  Omit or pass {} for actions that take no arguments.

    Returns:
        Human-readable result string describing the outcome.
    """
    platform = platform.lower().strip()
    action = action.strip()
    params = params or {}

    # ── Validation ────────────────────────────────────────────────────────────
    if platform not in DRIVERS:
        available = ", ".join(sorted(DRIVERS.keys()))
        return (
            f"❌ Unknown platform: '{platform}'\n"
            f"Available platforms: {available}\n\n"
            "Use driver_list to see all platforms and their actions."
        )

    # ── Session health gate ───────────────────────────────────────────────────
    health = check_session(platform, _vault)
    if health.status == SessionStatus.MISSING:
        return (
            f"○ No session for '{platform}'. Harvest it first:\n"
            f"  harvest_session(platform='{platform}')\n"
            f"or: agentreach harvest {platform}"
        )
    if health.status == SessionStatus.EXPIRED:
        return (
            f"❌ {platform.upper()} session is expired ({health.message})\n\n"
            f"Re-harvest: harvest_session(platform='{platform}')"
        )

    if ctx:
        await ctx.info(f"Dispatching {platform}.{action}({list(params.keys()) if params else ''})")

    # ── Load driver and dispatch ───────────────────────────────────────────────
    try:
        driver = get_driver(platform)
    except Exception as exc:
        return f"❌ Could not load driver for '{platform}': {exc}"

    # Warn on expiring session before running
    expiry_warning = ""
    if health.status == SessionStatus.EXPIRING_SOON:
        expiry_warning = (
            f"⚠️  Session expires in {health.days_remaining} days — "
            f"consider re-harvesting soon.\n\n"
        )

    # ── Resolve and call the action method ────────────────────────────────────
    if not hasattr(driver, action):
        caps = DRIVER_CAPABILITIES.get(platform, {})
        available_actions = list(caps.keys()) or [
            m for m in dir(driver) if not m.startswith("_")
        ]
        return (
            f"❌ Action '{action}' not found on {platform.upper()} driver.\n\n"
            f"Available actions: {', '.join(available_actions)}\n\n"
            f"Use driver_list(platform='{platform}') for descriptions."
        )

    method = getattr(driver, action)

    try:
        # Support both sync and async driver methods
        if asyncio.iscoroutinefunction(method):
            result = await asyncio.wait_for(method(**params), timeout=300)
        else:
            # Run sync method in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: method(**params)),
                timeout=300,
            )

        # ── Format result ─────────────────────────────────────────────────────
        return _format_action_result(platform, action, result, expiry_warning)

    except asyncio.TimeoutError:
        return (
            f"{expiry_warning}"
            f"⏰ {platform.upper()}.{action} timed out (5 min limit).\n\n"
            "The browser operation took too long. This can happen on slow connections "
            "or when the platform has changed its layout.\n"
            "Try re-harvesting the session if the issue persists."
        )
    except TypeError as exc:
        # Wrong parameters — give a helpful error
        import inspect
        try:
            sig = inspect.signature(method)
            params_hint = str(sig)
        except Exception:
            params_hint = "(signature unavailable)"
        return (
            f"❌ Parameter error calling {platform}.{action}: {exc}\n\n"
            f"Expected signature: {action}{params_hint}\n"
            f"You passed: {json.dumps(params, default=str, indent=2)}\n\n"
            f"Use driver_list(platform='{platform}') to see action descriptions."
        )
    except Exception as exc:
        return (
            f"{expiry_warning}"
            f"❌ {platform.upper()}.{action} failed:\n\n"
            f"{exc}\n\n"
            f"Traceback:\n{traceback.format_exc()}"
        )


def _format_action_result(platform: str, action: str, result: Any, prefix: str = "") -> str:
    """Convert a driver return value to a human-readable MCP response string."""
    if result is None:
        return f"{prefix}✅ {platform.upper()}.{action} completed (no return value)."

    # UploadResult dataclass (KDP, Etsy, Gumroad, Pinterest)
    if hasattr(result, "success") and hasattr(result, "message"):
        if result.success:
            parts = [f"{prefix}✅ {platform.upper()}.{action} succeeded.\n"]
            if result.message:
                parts.append(f"Message:    {result.message}")
            if getattr(result, "product_id", None):
                parts.append(f"Product ID: {result.product_id}")
            if getattr(result, "url", None):
                parts.append(f"URL:        {result.url}")
            return "\n".join(parts)
        else:
            parts = [f"{prefix}❌ {platform.upper()}.{action} failed.\n"]
            if result.message:
                parts.append(f"Message: {result.message}")
            if getattr(result, "error", None):
                parts.append(f"Error:   {result.error}")
            return "\n".join(parts)

    # bool result (verify_session, ensure_board_exists, etc.)
    if isinstance(result, bool):
        if result:
            return f"{prefix}✅ {platform.upper()}.{action} → True"
        else:
            return f"{prefix}❌ {platform.upper()}.{action} → False"

    # List result (get_bookshelf, list_products, etc.)
    if isinstance(result, list):
        if not result:
            return f"{prefix}📭 {platform.upper()}.{action} returned an empty list."
        lines = [f"{prefix}📋 {platform.upper()}.{action} returned {len(result)} item(s):\n"]
        for i, item in enumerate(result, 1):
            if isinstance(item, dict):
                item_str = "  " + "\n  ".join(f"{k}: {v}" for k, v in item.items())
            else:
                item_str = f"  {item}"
            lines.append(f"[{i}] {item_str}")
        return "\n".join(lines)

    # Dict result
    if isinstance(result, dict):
        lines = [f"{prefix}📦 {platform.upper()}.{action} result:\n"]
        lines.append(json.dumps(result, indent=2, default=str))
        return "\n".join(lines)

    # String or other
    return f"{prefix}✅ {platform.upper()}.{action}:\n{result}"


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCES — read-only vault data
# ─────────────────────────────────────────────────────────────────────────────

@mcp.resource(
    "agentreach://vault/status",
    name="vault_status_resource",
    description="Live vault status — all platforms with session health as JSON",
    mime_type="application/json",
)
def resource_vault_status() -> str:
    """Returns vault health data as JSON for programmatic access."""
    results = check_all(_vault)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vault_path": str(Path.home() / ".agentreach" / "vault"),
        "platforms": [_health_to_dict(h) for h in results],
        "summary": {
            "total": len(results),
            "healthy": sum(1 for h in results if h.status == SessionStatus.HEALTHY),
            "expiring_soon": sum(1 for h in results if h.status == SessionStatus.EXPIRING_SOON),
            "expired": sum(1 for h in results if h.status == SessionStatus.EXPIRED),
            "missing": sum(1 for h in results if h.status == SessionStatus.MISSING),
        },
    }
    return json.dumps(data, indent=2)


@mcp.resource(
    "agentreach://drivers",
    name="drivers_resource",
    description="List of all available platform drivers and their capabilities as JSON",
    mime_type="application/json",
)
def resource_drivers() -> str:
    """Returns driver capability data as JSON."""
    data = {
        "platforms": {
            p: {
                "driver_class": DRIVERS[p].__name__,
                "capabilities": DRIVER_CAPABILITIES.get(p, {}),
            }
            for p in sorted(DRIVERS.keys())
        }
    }
    return json.dumps(data, indent=2)


@mcp.resource(
    "agentreach://vault/{platform}",
    name="platform_session_resource",
    description="Health info for a specific platform session (no secrets — metadata only)",
    mime_type="application/json",
)
def resource_platform_session(platform: str) -> str:
    """Returns health metadata for a single platform's session."""
    health = check_session(platform.lower(), _vault)
    return json.dumps(_health_to_dict(health), indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS — reusable prompt templates
# ─────────────────────────────────────────────────────────────────────────────

@mcp.prompt(
    name="publish_product",
    description=(
        "Prompt template for publishing a digital product to multiple platforms "
        "(KDP, Etsy, Gumroad) using AgentReach. Guides the agent through checking "
        "session health, running upload actions, and handling errors."
    ),
)
def prompt_publish_product(
    product_title: str,
    platforms: str = "kdp, etsy, gumroad",
) -> str:
    """
    Args:
        product_title: The product title to publish.
        platforms:     Comma-separated list of target platforms.
    """
    return f"""You are publishing "{product_title}" to: {platforms}.

Use AgentReach MCP tools in this order:

1. **Check sessions**: Call vault_health to verify all target platforms have healthy sessions.
   - If any session is missing or expired, call harvest_session for that platform first.

2. **Verify active**: For each target platform, call platform_login to confirm the session
   is live (not just vault-present).

3. **Execute uploads**: For each platform, call platform_action with the appropriate action:
   - KDP: action="create_paperback", params={{title, manuscript_path, cover_path, ...}}
   - Etsy: action="create_listing", params={{title, description, price, digital_files, ...}}
   - Gumroad: action="create_product", params={{name, description, price, file_path, ...}}

4. **Report**: Summarise results for all platforms — successes with URLs/IDs, any failures
   with remediation steps.

If any platform fails with a session error, instruct the user to run:
  harvest_session(platform="<platform>")
and retry after re-harvest completes.
"""


@mcp.prompt(
    name="platform_health_check",
    description=(
        "Prompt template for running a full AgentReach health audit: checks all "
        "sessions, flags anything expiring or expired, and generates a re-harvest plan."
    ),
)
def prompt_platform_health_check() -> str:
    return """Run a full AgentReach platform health audit:

1. Call vault_health (no arguments) to check all known platforms.
2. Identify any platforms with status: expired, expiring_soon, or missing.
3. For expired/missing platforms: list the harvest command needed.
4. For expiring_soon platforms: note days remaining and suggest re-harvest timing.
5. Present a clean summary table: Platform | Status | Days Remaining | Action Needed.
6. If everything is healthy, confirm the vault is in good shape.

Be proactive: if platforms are expiring in < 7 days, recommend scheduling a re-harvest
before the session fails mid-operation.
"""


@mcp.prompt(
    name="harvest_all_platforms",
    description="Step-by-step guide for harvesting sessions across all supported platforms.",
)
def prompt_harvest_all_platforms() -> str:
    platforms = sorted(DRIVERS.keys())
    steps = "\n".join(
        f"  {i+1}. harvest_session(platform='{p}')" for i, p in enumerate(platforms)
    )
    return f"""Bootstrap AgentReach for all supported platforms.

This is a one-time setup. After completing, all platforms run autonomously.

Platforms to harvest: {', '.join(platforms)}

For each platform:
{steps}

Each harvest will:
- Open a visible browser window
- Wait for you to log in normally (5 minute window)
- Save your encrypted session to ~/.agentreach/vault/

Special notes:
- KDP: After logging in, navigate to "Create a new title" to capture step-up auth cookies.
- Reddit: Session lasts ~90 days — lowest maintenance.
- Pinterest: Session lasts ~60 days.

When all harvests complete, run vault_health to confirm everything is green.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run the AgentReach MCP server (stdio transport for desktop clients)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

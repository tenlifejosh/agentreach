"""
AgentReach — Gumroad Driver
API for reading sales/products. Browser-based session for creating products.
(Gumroad's v2 API does not support POST /products — create requires web UI)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from ..vault.store import SessionVault
from ..browser.session import platform_context
from ..browser.uploader import upload_file, wait_for_upload_complete
from .base import BasePlatformDriver, UploadResult


logger = logging.getLogger(__name__)


@dataclass
class GumroadProduct:
    name: str
    description: str
    price_cents: int          # e.g. 799 for $7.99
    custom_url: str = ""      # Custom URL slug
    file_path: Optional[str] = None
    cover_image_path: Optional[str] = None


class GumroadDriver(BasePlatformDriver):
    platform_name = "gumroad"
    API_BASE = "https://api.gumroad.com/v2"

    DASHBOARD_URL = "https://gumroad.com/products"
    NEW_PRODUCT_URL = "https://gumroad.com/products/new"

    def __init__(self, access_token: Optional[str] = None, vault: Optional[SessionVault] = None):
        super().__init__(vault)
        self._access_token = access_token

    def _get_token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
        import os
        env_token = os.environ.get("GUMROAD_ACCESS_TOKEN")
        if env_token:
            return env_token
        try:
            session = self.vault.load("gumroad")
        except Exception as exc:
            logger.error("Failed to load Gumroad session from vault: %s", exc)
            session = None
        if session:
            return session.get("access_token")
        return None

    def _get_seller_subdomain(self) -> Optional[str]:
        """
        Get the seller's Gumroad subdomain.
        Loaded from vault session (populated during verify_session) or env var.
        Never hardcoded.
        """
        import os
        env_sub = os.environ.get("GUMROAD_SELLER_SUBDOMAIN")
        if env_sub:
            return env_sub
        try:
            session = self.vault.load("gumroad")
        except Exception:
            session = None
        if session:
            return session.get("seller_subdomain")
        return None

    def save_token(self, token: str) -> None:
        """Save a Gumroad API token to the vault."""
        try:
            existing = self.vault.load("gumroad") or {}
        except Exception:
            existing = {}
        existing["access_token"] = token
        self.vault.save("gumroad", existing)
        self._access_token = token
        print("✅ Gumroad API token saved to vault.")

    async def verify_session(self) -> bool:
        """
        Verify API token is valid (read access).
        Also fetches and stores the seller's subdomain for use in product URLs.
        """
        token = self._get_token()
        if not token:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.API_BASE}/user",
                    params={"access_token": token},
                    timeout=10,
                )
                if resp.status_code != 200:
                    return False
                data = resp.json()
                if not isinstance(data, dict):
                    logger.warning("Gumroad verify_session returned non-dict JSON payload: %r", type(data))
                    return True

                # Store the seller subdomain so we never have to hardcode it.
                user = data.get("user") if isinstance(data.get("user"), dict) else {}
                profile_url = user.get("profile_url") or user.get("url") or ""
                subdomain = ""
                if isinstance(profile_url, str) and "gumroad.com/" in profile_url:
                    subdomain = profile_url.split("gumroad.com/")[-1].strip("/")

                if subdomain:
                    try:
                        existing = self.vault.load("gumroad") or {}
                    except Exception:
                        existing = {}
                    try:
                        existing["seller_subdomain"] = subdomain
                        self.vault.save("gumroad", existing)
                    except Exception as exc:
                        logger.warning("Failed to persist Gumroad seller subdomain %r: %s", subdomain, exc)
                return True
        except Exception as exc:
            logger.error("Gumroad verify_session failed: %s", exc)
            return False

    async def verify_browser_session(self) -> bool:
        """Verify the browser session (cookie-based) is still valid."""
        try:
            async with platform_context("gumroad", self.vault) as (ctx, page):
                await page.goto(self.DASHBOARD_URL, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                return "login" not in page.url and "gumroad.com" in page.url
        except Exception as exc:
            logger.error("Gumroad verify_browser_session failed: %s", exc)
            return False

    async def list_products(self) -> list[dict]:
        """List all Gumroad products via API."""
        token = self._get_token()
        if not token:
            raise ValueError("No Gumroad API token found. Run: agentreach gumroad set-token <token>")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.API_BASE}/products",
                    params={"access_token": token},
                    timeout=15,
                )
                resp.raise_for_status()
                return resp.json().get("products", [])
        except httpx.HTTPStatusError as exc:
            logger.error("Gumroad list_products HTTP error: %s", exc)
            raise RuntimeError(f"Gumroad API error listing products: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.error("Gumroad list_products failed: %s", exc)
            raise

    async def create_product(self, product: GumroadProduct) -> UploadResult:
        """
        Create a new Gumroad product via headless browser (API doesn't support POST).
        Requires a harvested browser session: agentreach harvest gumroad

        The returned URL is extracted from the page after creation, so it's always
        correct for the authenticated seller — never hardcoded.
        """
        try:
            async with platform_context("gumroad", self.vault) as (ctx, page):
                try:
                    await page.goto(self.NEW_PRODUCT_URL, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Product name — use placeholder selector (ID is dynamic)
                    name_input = page.locator('input[placeholder="Name of product"]').first
                    await name_input.wait_for(timeout=15000)
                    await name_input.fill(product.name)
                    await page.wait_for_timeout(500)

                    # Price
                    price_dollars = product.price_cents / 100
                    price_input = page.locator('input[placeholder="Price your product"]').first
                    await price_input.fill(str(price_dollars))
                    await page.wait_for_timeout(300)

                    # Next / Create button
                    create_btn = page.locator(
                        'button:has-text("Next"), button:has-text("Create"), button[type="submit"]'
                    ).first
                    await create_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    await page.wait_for_timeout(2000)

                    # Get product ID from URL (now that we're on the product edit page)
                    product_url_after_create = page.url
                    product_id = None
                    if "/products/" in product_url_after_create:
                        product_id = (
                            product_url_after_create.split("/products/")[1]
                            .split("/")[0]
                            .split("?")[0]
                        )

                    # Description
                    if product.description:
                        try:
                            desc_area = page.locator('[contenteditable="true"]').first
                            await desc_area.click()
                            await page.keyboard.press("Control+a")
                            await desc_area.type(product.description)
                            await page.wait_for_timeout(500)
                        except Exception as exc:
                            logger.warning("Could not fill Gumroad description: %s", exc)

                    # Upload digital file
                    if product.file_path:
                        file_path = Path(product.file_path)
                        if file_path.exists():
                            uploaded = await upload_file(
                                page,
                                file_path,
                                trigger_selector='button:has-text("Upload"), [class*="upload"]',
                                input_selector='input[type="file"]',
                            )
                            if uploaded:
                                await wait_for_upload_complete(page, timeout=120000)
                                await page.wait_for_timeout(2000)
                            else:
                                logger.warning(
                                    "Gumroad: file upload attempt returned False for %s", file_path
                                )
                        else:
                            logger.warning("Gumroad: file not found at %s", product.file_path)

                    # Save
                    save_btn = page.locator(
                        'button:has-text("Save changes"), button:has-text("Save"), button:has-text("Publish")'
                    ).first
                    await save_btn.click()
                    await page.wait_for_timeout(3000)

                    # Build the product URL dynamically — never hardcoded
                    # Try to read the canonical URL from the page first
                    gumroad_url = None

                    # Look for the share/preview URL shown on the edit page
                    try:
                        share_link = page.locator('a[href*="gumroad.com/l/"]').first
                        if await share_link.count() > 0:
                            gumroad_url = await share_link.get_attribute("href")
                    except Exception as exc:
                        logger.debug("Could not read Gumroad share link from page: %s", exc)

                    # Fallback: construct from seller subdomain (loaded from API during verify_session)
                    if not gumroad_url:
                        subdomain = self._get_seller_subdomain()
                        slug = product.custom_url or product_id
                        if subdomain and slug:
                            gumroad_url = f"https://{subdomain}.gumroad.com/l/{slug}"
                        elif slug:
                            # Last resort: use the generic gumroad.com/l/ URL
                            gumroad_url = f"https://gumroad.com/l/{slug}"

                    return UploadResult(
                        success=True,
                        platform="gumroad",
                        product_id=product_id,
                        url=gumroad_url,
                        message=f"'{product.name}' published to Gumroad",
                    )

                except Exception as e:
                    logger.error("Gumroad create_product browser error: %s", e, exc_info=True)
                    return UploadResult(
                        success=False,
                        platform="gumroad",
                        error=(
                            f"Browser session error. "
                            f"If session is stale, run: agentreach harvest gumroad\n"
                            f"Error: {e}"
                        ),
                    )
        except Exception as e:
            logger.error("Gumroad create_product context error: %s", e, exc_info=True)
            return UploadResult(
                success=False,
                platform="gumroad",
                error=f"Browser session required. Run: agentreach harvest gumroad\nError: {e}",
            )

    async def get_sales(self, after: Optional[str] = None) -> dict:
        """Get sales data via API."""
        token = self._get_token()
        if not token:
            raise ValueError("No Gumroad API token. Run: agentreach gumroad set-token <token>")
        params = {"access_token": token}
        if after:
            params["after"] = after
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.API_BASE}/sales", params=params, timeout=15)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Gumroad get_sales HTTP error: %s", exc)
            raise RuntimeError(
                f"Gumroad API error fetching sales: {exc.response.status_code} {exc.response.text}"
            ) from exc
        except Exception as exc:
            logger.error("Gumroad get_sales failed: %s", exc)
            raise

    def publish_product(self, product: GumroadProduct) -> UploadResult:
        """Synchronous wrapper for create_product."""
        return asyncio.run(self.create_product(product))

    def check_sales(self, after: Optional[str] = None) -> dict:
        """Synchronous wrapper for get_sales."""
        return asyncio.run(self.get_sales(after))

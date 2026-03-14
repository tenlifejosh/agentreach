"""
AgentReach — Gumroad Driver
API for reading sales/products. Browser-based session for creating products.
(Gumroad's v2 API does not support POST /products — create requires web UI)
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from ..vault.store import SessionVault
from ..browser.session import platform_context
from ..browser.uploader import upload_file, wait_for_upload_complete
from .base import BasePlatformDriver, UploadResult


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
        session = self.vault.load("gumroad")
        if session:
            return session.get("access_token")
        return None

    def save_token(self, token: str) -> None:
        """Save a Gumroad API token to the vault."""
        existing = self.vault.load("gumroad") or {}
        existing["access_token"] = token
        self.vault.save("gumroad", existing)
        self._access_token = token
        print(f"✅ Gumroad API token saved to vault.")

    async def verify_session(self) -> bool:
        """Verify API token is valid (read access)."""
        token = self._get_token()
        if not token:
            return False
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/user",
                params={"access_token": token},
                timeout=10,
            )
            return resp.status_code == 200

    async def verify_browser_session(self) -> bool:
        """Verify the browser session (cookie-based) is still valid."""
        try:
            async with platform_context("gumroad", self.vault) as (ctx, page):
                await page.goto(self.DASHBOARD_URL, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                return "login" not in page.url and "gumroad.com" in page.url
        except Exception:
            return False

    async def list_products(self) -> list[dict]:
        """List all Gumroad products via API."""
        token = self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/products",
                params={"access_token": token},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("products", [])

    async def create_product(self, product: GumroadProduct) -> UploadResult:
        """
        Create a new Gumroad product via headless browser (API doesn't support POST).
        Requires a harvested browser session: agentreach harvest gumroad
        """
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
                create_btn = page.locator('button:has-text("Next"), button:has-text("Create"), button[type="submit"]').first
                await create_btn.click()
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_timeout(2000)

                # Get product ID from URL
                product_url = page.url
                product_id = None
                if "/products/" in product_url:
                    product_id = product_url.split("/products/")[1].split("/")[0].split("?")[0]

                # Description
                if product.description:
                    try:
                        desc_area = page.locator('[contenteditable="true"]').first
                        await desc_area.click()
                        await page.keyboard.press("Control+a")
                        await desc_area.type(product.description)
                        await page.wait_for_timeout(500)
                    except Exception:
                        pass

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

                # Save
                save_btn = page.locator('button:has-text("Save changes"), button:has-text("Save"), button:has-text("Publish")').first
                await save_btn.click()
                await page.wait_for_timeout(3000)

                gumroad_url = f"https://tenlifejosh.gumroad.com/l/{product.custom_url or product_id}"

                return UploadResult(
                    success=True,
                    platform="gumroad",
                    product_id=product_id,
                    url=gumroad_url,
                    message=f"'{product.name}' published to Gumroad",
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    platform="gumroad",
                    error=f"Browser session required. Run: agentreach harvest gumroad\nError: {str(e)}",
                )

    async def get_sales(self, after: Optional[str] = None) -> dict:
        """Get sales data via API."""
        token = self._get_token()
        params = {"access_token": token}
        if after:
            params["after"] = after
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.API_BASE}/sales", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()

    def publish_product(self, product: GumroadProduct) -> UploadResult:
        """Synchronous wrapper for create_product."""
        return asyncio.run(self.create_product(product))

    def check_sales(self, after: Optional[str] = None) -> dict:
        """Synchronous wrapper for get_sales."""
        return asyncio.run(self.get_sales(after))

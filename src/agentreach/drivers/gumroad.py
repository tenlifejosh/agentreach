"""
AgentReach — Gumroad Driver
API-first (v2 REST API). Cookie fallback for operations not covered by API.
Gumroad's API supports: create product, update product, get sales.
File upload requires a separate API call.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from ..vault.store import SessionVault
from .base import BasePlatformDriver, UploadResult


@dataclass
class GumroadProduct:
    name: str
    description: str
    price_cents: int          # e.g. 799 for $7.99
    url: str = ""             # Custom URL slug
    published: bool = True
    file_path: Optional[str] = None


class GumroadDriver(BasePlatformDriver):
    platform_name = "gumroad"
    API_BASE = "https://api.gumroad.com/v2"

    def __init__(self, access_token: Optional[str] = None, vault: Optional[SessionVault] = None):
        super().__init__(vault)
        self._access_token = access_token

    def _get_token(self) -> Optional[str]:
        """Get API access token — from constructor, vault, or env."""
        if self._access_token:
            return self._access_token

        import os
        env_token = os.environ.get("GUMROAD_ACCESS_TOKEN")
        if env_token:
            return env_token

        # Try loading from vault
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

    async def list_products(self) -> list[dict]:
        """List all Gumroad products."""
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
        Create a new Gumroad product and optionally upload a digital file.
        Returns the product ID and URL on success.
        """
        token = self._get_token()
        if not token:
            return UploadResult(
                success=False,
                platform="gumroad",
                error="No Gumroad access token. Run: agentreach gumroad set-token <token>",
            )

        async with httpx.AsyncClient() as client:
            # Step 1: Create the product
            payload = {
                "access_token": token,
                "name": product.name,
                "description": product.description,
                "price": product.price_cents,
                "published": str(product.published).lower(),
            }
            if product.url:
                payload["url"] = product.url

            resp = await client.post(
                f"{self.API_BASE}/products",
                data=payload,
                timeout=30,
            )

            if resp.status_code != 201:
                return UploadResult(
                    success=False,
                    platform="gumroad",
                    error=f"Failed to create product: {resp.status_code} {resp.text}",
                )

            product_data = resp.json().get("product", {})
            product_id = product_data.get("id")
            product_url = product_data.get("short_url") or product_data.get("url")

            # Step 2: Upload digital file if provided
            if product.file_path:
                file_path = Path(product.file_path)
                if file_path.exists():
                    upload_result = await self._upload_file(client, token, product_id, file_path)
                    if not upload_result:
                        return UploadResult(
                            success=False,
                            platform="gumroad",
                            product_id=product_id,
                            url=product_url,
                            error=f"Product created (ID: {product_id}) but file upload failed. Upload manually at gumroad.com/products/{product_id}/edit",
                        )

        return UploadResult(
            success=True,
            platform="gumroad",
            product_id=product_id,
            url=product_url,
            message=f"'{product.name}' live on Gumroad at {product_url}",
        )

    async def _upload_file(
        self,
        client: httpx.AsyncClient,
        token: str,
        product_id: str,
        file_path: Path,
    ) -> bool:
        """Upload a digital file to an existing Gumroad product."""
        try:
            with open(file_path, "rb") as f:
                resp = await client.post(
                    f"{self.API_BASE}/products/{product_id}/product_files",
                    data={"access_token": token},
                    files={"file": (file_path.name, f, "application/octet-stream")},
                    timeout=120,
                )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    async def get_sales(self, after: Optional[str] = None) -> dict:
        """Get sales data. after = ISO date string to filter."""
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

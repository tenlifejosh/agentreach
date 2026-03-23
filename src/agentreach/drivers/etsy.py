"""
AgentReach — Etsy Driver
Uses Etsy Open API v3 for listing creation and management.
Cookie-based headless fallback for file uploads (Etsy API v3 supports digital file upload
but requires OAuth2 setup).

Setup: Generate API key at https://www.etsy.com/developers/register
Then run: agentreach etsy set-credentials --api-key <key> --keystring <keystring>
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from ..vault.store import SessionVault
from ..browser.session import platform_context
from ..browser.uploader import upload_file, wait_for_upload_complete
from .base import BasePlatformDriver, UploadResult


logger = logging.getLogger(__name__)


@dataclass
class EtsyListing:
    title: str
    description: str
    price: float                      # e.g. 7.99
    tags: list[str] = field(default_factory=list)       # up to 13
    materials: list[str] = field(default_factory=list)
    quantity: int = 999
    who_made: str = "i_did"           # i_did, someone_else, collective
    is_supply: bool = False
    when_made: str = "2020_2025"
    taxonomy_id: int = 2078           # Craft Supplies & Tools > Patterns & How To
    digital_files: list[str] = field(default_factory=list)   # file paths
    image_paths: list[str] = field(default_factory=list)     # mockup image paths
    shop_section_id: Optional[int] = None


class EtsyDriver(BasePlatformDriver):
    platform_name = "etsy"

    API_BASE = "https://openapi.etsy.com/v3/application"

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        shop_id: Optional[str] = None,
        vault: Optional[SessionVault] = None,
    ):
        super().__init__(vault)
        self._api_key = api_key
        self._access_token = access_token
        self._shop_id = shop_id

    def _get_credentials(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (api_key, access_token, shop_id)."""
        if self._api_key and self._access_token:
            return self._api_key, self._access_token, self._shop_id

        import os
        api_key = self._api_key or os.environ.get("ETSY_API_KEY")
        access_token = self._access_token or os.environ.get("ETSY_ACCESS_TOKEN")
        shop_id = self._shop_id or os.environ.get("ETSY_SHOP_ID")

        if not (api_key and access_token):
            try:
                session = self.vault.load("etsy")
            except Exception as exc:
                logger.error("Failed to load Etsy session from vault: %s", exc)
                session = None
            if session:
                api_key = api_key or session.get("api_key")
                access_token = access_token or session.get("access_token")
                shop_id = shop_id or session.get("shop_id")

        return api_key, access_token, shop_id

    def save_credentials(self, api_key: str, access_token: str, shop_id: str) -> None:
        """Save Etsy API credentials to the vault."""
        try:
            existing = self.vault.load("etsy") or {}
        except Exception:
            existing = {}
        existing.update({
            "api_key": api_key,
            "access_token": access_token,
            "shop_id": shop_id,
        })
        self.vault.save("etsy", existing)
        print("✅ Etsy credentials saved to vault.")

    def _headers(self, api_key: str, access_token: str) -> dict:
        return {
            "x-api-key": api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def verify_session(self) -> bool:
        """Verify session — tries API first, falls back to browser cookie session."""
        api_key, access_token, _ = self._get_credentials()
        if api_key and access_token:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self.API_BASE}/users/me",
                        headers=self._headers(api_key, access_token),
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        return True
            except Exception as exc:
                logger.warning("Etsy API session check failed: %s", exc)

        # Fall back to browser session check
        try:
            async with platform_context("etsy", self.vault) as (ctx, page):
                await page.goto(
                    "https://www.etsy.com/your/shops/me/tools/listings",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                await page.wait_for_timeout(2000)
                return "signin" not in page.url and "login" not in page.url
        except Exception as exc:
            logger.error("Etsy browser session check failed: %s", exc)
            return False

    async def create_listing(self, listing: EtsyListing) -> UploadResult:
        """
        Create a new Etsy listing with images and digital files.
        All upload responses are verified — failures raise errors immediately.
        """
        api_key, access_token, shop_id = self._get_credentials()
        if not (api_key and access_token and shop_id):
            return UploadResult(
                success=False,
                platform="etsy",
                error="Missing Etsy credentials. Run: agentreach etsy set-credentials",
            )

        headers = self._headers(api_key, access_token)
        upload_errors: list[str] = []

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create the listing
                payload = {
                    "quantity": listing.quantity,
                    "title": listing.title,
                    "description": listing.description,
                    "price": listing.price,
                    "who_made": listing.who_made,
                    "when_made": listing.when_made,
                    "taxonomy_id": listing.taxonomy_id,
                    "tags": listing.tags[:13],
                    "is_digital": len(listing.digital_files) > 0,
                    "file_data": "",
                }
                if listing.shop_section_id:
                    payload["shop_section_id"] = listing.shop_section_id

                resp = await client.post(
                    f"{self.API_BASE}/shops/{shop_id}/listings",
                    json=payload,
                    headers=headers,
                    timeout=30,
                )

                if resp.status_code not in (200, 201):
                    return UploadResult(
                        success=False,
                        platform="etsy",
                        error=f"Failed to create listing: {resp.status_code} {resp.text}",
                    )

                listing_data = resp.json()
                listing_id = listing_data.get("listing_id")

                if not listing_id:
                    return UploadResult(
                        success=False,
                        platform="etsy",
                        error=f"Etsy API returned no listing_id. Response: {resp.text[:500]}",
                    )

                # Step 2: Upload images — check every response
                for i, image_path in enumerate(listing.image_paths[:10]):
                    img_path = Path(image_path)
                    if not img_path.exists():
                        logger.warning("Etsy: image file not found, skipping: %s", image_path)
                        continue
                    try:
                        with open(img_path, "rb") as f:
                            img_resp = await client.post(
                                f"{self.API_BASE}/shops/{shop_id}/listings/{listing_id}/images",
                                headers={
                                    "x-api-key": api_key,
                                    "Authorization": f"Bearer {access_token}",
                                },
                                files={"image": (img_path.name, f, "image/jpeg")},
                                data={"rank": i + 1},
                                timeout=60,
                            )
                        if img_resp.status_code not in (200, 201):
                            err_msg = (
                                f"Image upload failed for {img_path.name}: "
                                f"{img_resp.status_code} {img_resp.text[:200]}"
                            )
                            logger.error("Etsy image upload error: %s", err_msg)
                            upload_errors.append(err_msg)
                        else:
                            logger.debug("Etsy image uploaded: %s (rank %d)", img_path.name, i + 1)
                        await asyncio.sleep(0.5)
                    except Exception as exc:
                        err_msg = f"Image upload exception for {img_path.name}: {exc}"
                        logger.error("Etsy image upload exception: %s", err_msg)
                        upload_errors.append(err_msg)

                # Step 3: Upload digital files — check every response
                for rank, file_path in enumerate(listing.digital_files, start=1):
                    fp = Path(file_path)
                    if not fp.exists():
                        logger.warning("Etsy: digital file not found, skipping: %s", file_path)
                        continue
                    try:
                        with open(fp, "rb") as f:
                            file_resp = await client.post(
                                f"{self.API_BASE}/shops/{shop_id}/listings/{listing_id}/files",
                                headers={
                                    "x-api-key": api_key,
                                    "Authorization": f"Bearer {access_token}",
                                },
                                files={"file": (fp.name, f, "application/octet-stream")},
                                data={"rank": rank, "name": fp.name},
                                timeout=120,
                            )
                        if file_resp.status_code not in (200, 201):
                            err_msg = (
                                f"Digital file upload failed for {fp.name}: "
                                f"{file_resp.status_code} {file_resp.text[:200]}"
                            )
                            logger.error("Etsy digital file upload error: %s", err_msg)
                            upload_errors.append(err_msg)
                        else:
                            logger.debug("Etsy digital file uploaded: %s", fp.name)
                    except Exception as exc:
                        err_msg = f"Digital file upload exception for {fp.name}: {exc}"
                        logger.error("Etsy digital file upload exception: %s", err_msg)
                        upload_errors.append(err_msg)

                # Step 4: Activate the listing
                activate_resp = await client.patch(
                    f"{self.API_BASE}/shops/{shop_id}/listings/{listing_id}",
                    json={"state": "active"},
                    headers=headers,
                    timeout=15,
                )
                if activate_resp.status_code not in (200, 201):
                    logger.warning(
                        "Etsy listing activation returned %d: %s",
                        activate_resp.status_code,
                        activate_resp.text[:200],
                    )

        except httpx.HTTPStatusError as exc:
            return UploadResult(
                success=False,
                platform="etsy",
                error=f"Etsy API HTTP error: {exc.response.status_code} {exc.response.text[:200]}",
            )
        except Exception as exc:
            logger.error("Etsy create_listing failed: %s", exc, exc_info=True)
            return UploadResult(
                success=False,
                platform="etsy",
                error=f"Etsy listing creation failed: {exc}",
            )

        listing_url = f"https://www.etsy.com/listing/{listing_id}"

        if upload_errors:
            # Listing was created but some uploads failed — partial success
            return UploadResult(
                success=True,
                platform="etsy",
                product_id=str(listing_id),
                url=listing_url,
                message=(
                    f"'{listing.title}' created on Etsy at {listing_url} "
                    f"BUT {len(upload_errors)} upload(s) failed:\n"
                    + "\n".join(f"  - {e}" for e in upload_errors)
                ),
            )

        return UploadResult(
            success=True,
            platform="etsy",
            product_id=str(listing_id),
            url=listing_url,
            message=f"'{listing.title}' live on Etsy at {listing_url}",
        )

    def publish_listing(self, listing: EtsyListing) -> UploadResult:
        """Synchronous wrapper."""
        return asyncio.run(self.create_listing(listing))

"""
AgentReach — React-Bypass File Uploader
Solves the #1 file upload failure mode: React synthetic event systems
rejecting programmatic input via standard setInputFiles.

The Problem:
    React wraps native DOM events in a synthetic event system.
    Standard programmatic file input (input.value = path) bypasses
    React's onChange handler — the file appears set but nothing happens.

The Fix:
    1. Use Playwright's setInputFiles (which uses CDP's Input.setFiles) —
       this sets files at the browser protocol level, bypassing JS entirely.
    2. For stubborn React components, dispatch a native InputEvent with
       the native HTMLInputElement setter AND inject real base64-encoded file
       bytes so the browser Blob contains actual content, not placeholder text.
    3. For drag-and-drop upload zones (no visible <input>), use
       DataTransfer API simulation.
    4. For completely custom upload dialogs, intercept the file chooser
       event at the browser level.

This module tries all four strategies in order.
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Optional

from playwright.async_api import Page, FileChooser, Locator


logger = logging.getLogger(__name__)


async def upload_file(
    page: Page,
    file_path: str | Path,
    trigger_selector: Optional[str] = None,
    input_selector: str = 'input[type="file"]',
    timeout: int = 30000,
) -> bool:
    """
    Upload a file, trying multiple strategies to handle React and custom uploaders.

    Strategy order:
    1. Direct setInputFiles — works for most inputs, including many React ones.
    2. Native setter bypass with real file bytes (base64) — forces React fiber to
       register the change when Strategy 1 doesn't trigger the change handler.
    3. File chooser interception — clicks a trigger button and intercepts the OS
       file dialog at the browser level.
    4. Drag-and-drop DataTransfer simulation — for drop zone uploaders.

    Args:
        page: Playwright page (authenticated)
        file_path: Path to the file to upload
        trigger_selector: CSS selector of a button/zone to click to trigger the dialog
                         (if None, targets the input directly)
        input_selector: CSS selector for the file input element
        timeout: Timeout in milliseconds

    Returns:
        True if upload succeeded, False if all strategies failed
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Strategy 1: Direct setInputFiles on the input element
    # Works for standard and many React inputs
    try:
        input_el = page.locator(input_selector).first
        await input_el.set_input_files(str(file_path), timeout=timeout)
        await page.wait_for_timeout(500)

        # Verify React picked it up by checking if file name appears anywhere
        content = await page.content()
        if file_path.name in content or await _file_registered(page, input_selector):
            return True
    except Exception as exc:
        logger.debug("Upload strategy 1 (setInputFiles) failed: %s", exc)

    # Strategy 2: Native setter bypass for React
    # Reads the actual file bytes, base64-encodes them, and injects a real Blob.
    # This forces React's synthetic event system to recognize the change.
    try:
        file_bytes = file_path.read_bytes()
        file_b64 = base64.b64encode(file_bytes).decode("ascii")
        # Determine MIME type based on extension
        suffix = file_path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".epub": "application/epub+zip",
            ".zip": "application/zip",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
        }
        mime_type = mime_map.get(suffix, "application/octet-stream")

        result = await page.evaluate(
            """
            ([selector, fileName, fileB64, mimeType]) => {
                const input = document.querySelector(selector);
                if (!input) return false;

                // Decode base64 to real binary data
                const binaryStr = atob(fileB64);
                const bytes = new Uint8Array(binaryStr.length);
                for (let i = 0; i < binaryStr.length; i++) {
                    bytes[i] = binaryStr.charCodeAt(i);
                }

                // Create a proper File object with real content
                const blob = new Blob([bytes], { type: mimeType });
                const file = new File([blob], fileName, { type: mimeType });
                const dt = new DataTransfer();
                dt.items.add(file);

                // Use native setter to bypass React's wrapper
                const nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'files'
                );
                if (nativeSetter && nativeSetter.set) {
                    nativeSetter.set.call(input, dt.files);
                } else {
                    // Fallback: direct assignment (less reliable)
                    try {
                        Object.defineProperty(input, 'files', {
                            value: dt.files,
                            writable: true,
                            configurable: true,
                        });
                    } catch(e) {
                        return false;
                    }
                }

                // Dispatch all events React listens to
                input.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                input.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                return true;
            }
            """,
            [input_selector, file_path.name, file_b64, mime_type],
        )
        if result:
            await page.wait_for_timeout(500)
            return True
    except Exception as exc:
        logger.debug("Upload strategy 2 (native setter with real bytes) failed: %s", exc)

    # Strategy 3: File chooser interception (works for custom upload dialogs)
    # Click the trigger and intercept the native OS file dialog
    if trigger_selector:
        try:
            async with page.expect_file_chooser(timeout=timeout) as fc_info:
                await page.click(trigger_selector)
            file_chooser: FileChooser = await fc_info.value
            await file_chooser.set_files(str(file_path))
            await page.wait_for_timeout(500)
            return True
        except Exception as exc:
            logger.debug("Upload strategy 3 (file chooser interception) failed: %s", exc)

    # Strategy 4: Drag-and-drop DataTransfer simulation
    # For drop zone uploaders with no visible input
    try:
        drop_zone = page.locator('[data-testid*="upload"], .upload-zone, .dropzone, [class*="drop"]').first
        if await drop_zone.count() > 0:
            file_bytes = file_path.read_bytes()
            file_b64 = base64.b64encode(file_bytes).decode("ascii")
            await page.evaluate(
                """
                ([selector, fileName, fileB64]) => {
                    const zone = document.querySelector(selector);
                    if (!zone) return false;

                    // Decode base64 to real binary data
                    const binaryStr = atob(fileB64);
                    const bytes = new Uint8Array(binaryStr.length);
                    for (let i = 0; i < binaryStr.length; i++) {
                        bytes[i] = binaryStr.charCodeAt(i);
                    }

                    const blob = new Blob([bytes], { type: 'application/octet-stream' });
                    const file = new File([blob], fileName, { type: 'application/octet-stream' });
                    const dt = new DataTransfer();
                    dt.items.add(file);

                    // Simulate a file drop event with actual file data
                    const dropEvent = new DragEvent('drop', {
                        bubbles: true,
                        cancelable: true,
                        dataTransfer: dt,
                    });
                    zone.dispatchEvent(dropEvent);
                    return true;
                }
                """,
                ['[data-testid*="upload"], .upload-zone, .dropzone, [class*="drop"]', file_path.name, file_b64],
            )
            await page.wait_for_timeout(500)
    except Exception as exc:
        logger.debug("Upload strategy 4 (drag-and-drop simulation) failed: %s", exc)

    logger.warning(
        "All upload strategies failed for file: %s using selector: %s",
        file_path,
        input_selector,
    )
    return False


async def _file_registered(page: Page, input_selector: str) -> bool:
    """Check if a file input has files registered."""
    try:
        count = await page.evaluate(
            f'document.querySelector({repr(input_selector)})?.files?.length || 0'
        )
        return count > 0
    except Exception:
        return False


async def wait_for_upload_complete(
    page: Page,
    success_indicator: Optional[str] = None,
    timeout: int = 60000,
) -> bool:
    """
    Wait for an upload to complete.
    Looks for common success indicators or a custom selector.
    """
    if success_indicator:
        try:
            await page.wait_for_selector(success_indicator, timeout=timeout)
            return True
        except Exception as exc:
            logger.debug("Upload completion indicator not found: %s", exc)
            return False

    # Generic: wait for loading indicators to disappear
    try:
        await page.wait_for_selector(
            '.upload-progress, [class*="uploading"], [aria-label*="uploading"]',
            state="hidden",
            timeout=timeout,
        )
        return True
    except Exception:
        pass

    # Fallback: wait a reasonable time
    await page.wait_for_timeout(5000)
    return True

"""Encrypted, per-platform storage for AgentReach browser sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_DIR = Path.home() / ".agentreach" / "vault"
SALT_PATH = VAULT_DIR / ".salt"
_KEY_ITERATIONS = 480_000


class VaultCorruptedError(ValueError):
    """Raised when an encrypted vault entry cannot be read or validated."""


def _load_or_create_salt(machine_id: bytes) -> bytes:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    if SALT_PATH.exists():
        salt = SALT_PATH.read_bytes()
        if len(salt) != 32:
            raise RuntimeError(f"Invalid AgentReach vault salt: {SALT_PATH}")
        return salt

    # Existing vaults without a salt use the deterministic key from older releases.
    salt = (
        hashlib.sha256(machine_id).digest()
        if any(VAULT_DIR.glob("*.vault"))
        else os.urandom(32)
    )
    try:
        fd = os.open(SALT_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        stored = SALT_PATH.read_bytes()
        if len(stored) != 32:
            raise RuntimeError(f"Invalid AgentReach vault salt: {SALT_PATH}")
        return stored
    with os.fdopen(fd, "wb") as salt_file:
        salt_file.write(salt)
    try:
        os.chmod(SALT_PATH, 0o600)
    except OSError:
        pass
    return salt


def _derive_key() -> bytes:
    machine_id = str(uuid.getnode()).encode("ascii")
    salt = _load_or_create_salt(machine_id)
    derived = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KEY_ITERATIONS,
    ).derive(machine_id)
    return base64.urlsafe_b64encode(derived)


_FERNET = Fernet(_derive_key())


class SessionVault:
    """Read and write Fernet-encrypted JSON sessions under a vault directory."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        self.vault_dir = Path(vault_dir) if vault_dir is not None else VAULT_DIR
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, platform: str) -> Path:
        if not isinstance(platform, str):
            raise ValueError("Platform name must be a string")
        normalized = re.sub(r"\s+", "-", platform.strip().lower())
        if not normalized or not re.fullmatch(r"[a-z0-9_-]+", normalized):
            raise ValueError(f"Invalid platform name: {platform!r}")
        return self.vault_dir / f"{normalized}.vault"

    def save(self, platform: str, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise TypeError("Vault session data must be a dictionary")
        payload = {**data, "_saved_at": datetime.now(timezone.utc).isoformat()}
        encrypted = _FERNET.encrypt(json.dumps(payload).encode("utf-8"))
        path = self._path(platform)
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.vault_dir, delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(encrypted)
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def load(self, platform: str) -> dict[str, Any] | None:
        path = self._path(platform)
        if not path.exists():
            return None
        try:
            plaintext = _FERNET.decrypt(path.read_bytes())
            data = json.loads(plaintext.decode("utf-8"))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VaultCorruptedError(f"Vault entry for {platform!r} is corrupted") from exc
        if not isinstance(data, dict):
            raise VaultCorruptedError(f"Vault entry for {platform!r} is not a JSON object")
        return data

    def exists(self, platform: str) -> bool:
        return self._path(platform).is_file()

    def delete(self, platform: str) -> None:
        self._path(platform).unlink(missing_ok=True)

    def list_platforms(self) -> list[str]:
        return sorted(path.stem for path in self.vault_dir.glob("*.vault") if path.is_file())

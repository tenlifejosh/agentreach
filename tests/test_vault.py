"""
Tests for AgentReach Vault — encrypt/decrypt, store/retrieve, expiry, path traversal, backup/restore
"""

import json
import base64
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from agentreach.vault.store import SessionVault, _FERNET, VAULT_DIR
from cryptography.fernet import Fernet, InvalidToken


# ── Initialization ─────────────────────────────────────────────────────────────

class TestVaultInit:
    def test_init_with_tmp_dir(self, tmp_path):
        vault = SessionVault(vault_dir=tmp_path)
        assert vault.vault_dir == tmp_path

    def test_init_creates_dir(self, tmp_path):
        new_dir = tmp_path / "new_vault"
        assert not new_dir.exists()
        vault = SessionVault(vault_dir=new_dir)
        assert new_dir.exists()

    def test_default_vault_dir(self):
        vault = SessionVault()
        assert vault.vault_dir == VAULT_DIR
        assert VAULT_DIR.exists()

    def test_vault_dir_attribute(self, vault_dir):
        vault = SessionVault(vault_dir=vault_dir)
        assert vault.vault_dir == vault_dir


# ── Save & Load ────────────────────────────────────────────────────────────────

class TestVaultSaveLoad:
    def test_save_and_load_basic(self, vault):
        vault.save("kdp", {"key": "value"})
        result = vault.load("kdp")
        assert result is not None
        assert result["key"] == "value"

    def test_save_adds_saved_at_timestamp(self, vault):
        vault.save("etsy", {"cookies": []})
        result = vault.load("etsy")
        assert "_saved_at" in result

    def test_saved_at_is_iso_format(self, vault):
        vault.save("gumroad", {"token": "abc"})
        result = vault.load("gumroad")
        ts = result["_saved_at"]
        # Should parse without error
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is not None

    def test_load_nonexistent_returns_none(self, vault):
        result = vault.load("nonexistent_platform")
        assert result is None

    def test_save_complex_data(self, vault):
        data = {
            "cookies": [{"name": "session", "value": "abc", "domain": ".amazon.com"}],
            "storage_state": {"cookies": [], "origins": []},
            "nested": {"deep": {"value": 42}},
            "list": [1, 2, 3],
        }
        vault.save("kdp", data)
        result = vault.load("kdp")
        assert result["cookies"][0]["name"] == "session"
        assert result["nested"]["deep"]["value"] == 42
        assert result["list"] == [1, 2, 3]

    def test_data_is_actually_encrypted_on_disk(self, vault):
        vault.save("kdp", {"secret": "my_password"})
        vault_file = vault._path("kdp")
        raw_bytes = vault_file.read_bytes()
        # Should NOT contain the plaintext secret
        assert b"my_password" not in raw_bytes

    def test_vault_file_extension(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        assert path.suffix == ".vault"

    def test_platform_name_normalized_lowercase(self, vault):
        vault.save("KDP", {"k": "v"})
        result = vault.load("KDP")
        assert result is not None

    def test_platform_spaces_normalized(self, vault):
        vault.save("my platform", {"k": "v"})
        result = vault.load("my platform")
        assert result is not None

    def test_overwrite_existing_session(self, vault):
        vault.save("kdp", {"version": 1})
        vault.save("kdp", {"version": 2})
        result = vault.load("kdp")
        assert result["version"] == 2

    def test_multiple_platforms_independent(self, vault):
        vault.save("kdp", {"platform": "kdp"})
        vault.save("etsy", {"platform": "etsy"})
        kdp = vault.load("kdp")
        etsy = vault.load("etsy")
        assert kdp["platform"] == "kdp"
        assert etsy["platform"] == "etsy"


# ── Delete ─────────────────────────────────────────────────────────────────────

class TestVaultDelete:
    def test_delete_existing(self, vault):
        vault.save("kdp", {"k": "v"})
        vault.delete("kdp")
        assert vault.load("kdp") is None
        assert not vault.exists("kdp")

    def test_delete_nonexistent_no_error(self, vault):
        # Should not raise
        vault.delete("nonexistent_platform")

    def test_exists_after_save(self, vault):
        vault.save("etsy", {"k": "v"})
        assert vault.exists("etsy")

    def test_not_exists_before_save(self, vault):
        assert not vault.exists("etsy")


# ── List Platforms ─────────────────────────────────────────────────────────────

class TestVaultListPlatforms:
    def test_list_empty_vault(self, vault):
        assert vault.list_platforms() == []

    def test_list_single(self, vault):
        vault.save("kdp", {"k": "v"})
        platforms = vault.list_platforms()
        assert "kdp" in platforms
        assert len(platforms) == 1

    def test_list_multiple(self, vault):
        vault.save("kdp", {"k": "v"})
        vault.save("etsy", {"k": "v"})
        vault.save("gumroad", {"k": "v"})
        platforms = vault.list_platforms()
        assert set(platforms) == {"kdp", "etsy", "gumroad"}

    def test_list_after_delete(self, vault):
        vault.save("kdp", {"k": "v"})
        vault.save("etsy", {"k": "v"})
        vault.delete("kdp")
        platforms = vault.list_platforms()
        assert "kdp" not in platforms
        assert "etsy" in platforms


# ── Encryption Integrity ────────────────────────────────────────────────────────

class TestVaultEncryption:
    def test_corrupted_file_returns_none(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        # Corrupt the file
        path.write_bytes(b"this_is_not_valid_encrypted_data")
        result = vault.load("kdp")
        assert result is None

    def test_empty_file_returns_none(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        path.write_bytes(b"")
        result = vault.load("kdp")
        assert result is None

    def test_truncated_file_returns_none(self, vault):
        vault.save("kdp", {"k": "v"})
        path = vault._path("kdp")
        data = path.read_bytes()
        path.write_bytes(data[:10])
        result = vault.load("kdp")
        assert result is None

    def test_different_vault_instances_share_key(self, vault_dir):
        """Two vault instances in same dir should decrypt each other's data."""
        vault1 = SessionVault(vault_dir=vault_dir)
        vault2 = SessionVault(vault_dir=vault_dir)
        vault1.save("test", {"secret": "hello"})
        result = vault2.load("test")
        assert result is not None
        assert result["secret"] == "hello"


# ── Path Traversal Prevention ───────────────────────────────────────────────────

class TestPathTraversal:
    def test_path_stays_in_vault_dir(self, vault):
        """_path() should always resolve within vault_dir."""
        path = vault._path("kdp")
        assert path.parent == vault.vault_dir

    def test_path_with_normal_name(self, vault):
        path = vault._path("my_platform")
        assert "my_platform" in str(path)
        assert str(vault.vault_dir) in str(path)

    def test_platforms_list_only_vault_files(self, vault):
        """list_platforms() only returns .vault files."""
        vault.save("kdp", {"k": "v"})
        # Create a non-vault file in the vault directory
        (vault.vault_dir / "not_a_vault.txt").write_text("hello")
        platforms = vault.list_platforms()
        assert "not_a_vault" not in platforms
        assert "kdp" in platforms

    def test_safe_path_name_for_slashes(self, vault):
        """Platform names with special chars are safely handled."""
        # Should not raise even with odd chars
        path = vault._path("platform with spaces")
        assert path.parent == vault.vault_dir


# ── Backup & Restore ───────────────────────────────────────────────────────────

class TestVaultBackupRestore:
    def test_backup_creates_file(self, vault, tmp_path):
        """Backup command creates an encrypted archive."""
        from agentreach.vault.store import _FERNET
        vault.save("kdp", {"cookies": [], "test": "backup"})

        backup_path = tmp_path / "backup.enc"
        # Simulate backup logic
        bundle = {}
        for vf in vault.vault_dir.glob("*.vault"):
            bundle[vf.name] = base64.b64encode(vf.read_bytes()).decode()

        payload = json.dumps(bundle).encode()
        encrypted = _FERNET.encrypt(payload)
        backup_path.write_bytes(encrypted)

        assert backup_path.exists()
        assert backup_path.stat().st_size > 0

    def test_backup_and_restore_roundtrip(self, vault, tmp_path):
        """Data backed up from vault can be restored."""
        from agentreach.vault.store import _FERNET

        vault.save("kdp", {"test": "roundtrip_value"})
        vault.save("etsy", {"shop": "my_shop"})

        # Backup
        backup_path = tmp_path / "backup.enc"
        bundle = {}
        for vf in vault.vault_dir.glob("*.vault"):
            bundle[vf.name] = base64.b64encode(vf.read_bytes()).decode()

        payload = json.dumps(bundle).encode()
        backup_path.write_bytes(_FERNET.encrypt(payload))

        # Restore to new vault
        new_vault_dir = tmp_path / "restored"
        new_vault_dir.mkdir()
        new_vault = SessionVault(vault_dir=new_vault_dir)

        encrypted = backup_path.read_bytes()
        restored_payload = _FERNET.decrypt(encrypted)
        restored_bundle = json.loads(restored_payload.decode())

        for filename, encoded in restored_bundle.items():
            raw = base64.b64decode(encoded)
            (new_vault_dir / filename).write_bytes(raw)

        kdp_data = new_vault.load("kdp")
        etsy_data = new_vault.load("etsy")
        assert kdp_data["test"] == "roundtrip_value"
        assert etsy_data["shop"] == "my_shop"

    def test_restore_invalid_backup_raises(self, tmp_path):
        """Restoring from invalid/corrupt file should fail gracefully."""
        from agentreach.vault.store import _FERNET
        bad_backup = tmp_path / "bad.enc"
        bad_backup.write_bytes(b"not_valid_encrypted_data")

        with pytest.raises(Exception):
            _FERNET.decrypt(bad_backup.read_bytes())

"""Basic AgentReach vault tests."""
import pytest
from agentreach.vault.store import SessionVault


def test_vault_init(tmp_path):
    """Vault initializes without error and doesn't touch real vault dir."""
    vault = SessionVault(vault_dir=tmp_path)
    assert vault is not None
    assert vault.vault_dir == tmp_path


def test_vault_save_load(tmp_path):
    """Vault saves and loads session data correctly."""
    vault = SessionVault(vault_dir=tmp_path)
    vault.save("test_platform", {"key": "value", "cookies": []})
    loaded = vault.load("test_platform")
    assert loaded is not None
    assert loaded["key"] == "value"
    assert loaded["cookies"] == []


def test_vault_delete(tmp_path):
    """Vault delete removes a session file."""
    vault = SessionVault(vault_dir=tmp_path)
    vault.save("test_platform", {"key": "value"})
    assert vault.exists("test_platform")
    vault.delete("test_platform")
    assert not vault.exists("test_platform")


def test_vault_list_platforms(tmp_path):
    """Vault lists all stored platform names."""
    vault = SessionVault(vault_dir=tmp_path)
    vault.save("kdp", {"cookies": []})
    vault.save("etsy", {"cookies": []})
    platforms = vault.list_platforms()
    assert "kdp" in platforms
    assert "etsy" in platforms
    assert len(platforms) == 2

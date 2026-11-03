"""test_crypto.py - Tests for crypto.py."""
import pytest
from cryptography.fernet import Fernet

from src import crypto


def test_missing_fernet_key_raises(monkeypatch):
    monkeypatch.delenv("FERNET_KEY", raising=False)
    with pytest.raises(crypto.FernetKeyMissingError):
        crypto.encrypt_api_key("sk-test")


def test_roundtrip_with_configured_key(monkeypatch):
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    token = crypto.encrypt_api_key("sk-test")
    assert token != "sk-test"
    assert crypto.decrypt_api_key(token) == "sk-test"


def test_wrong_key_raises_value_error(monkeypatch):
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    token = crypto.encrypt_api_key("sk-test")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        crypto.decrypt_api_key(token)


def test_no_static_fallback_key_in_module():
    assert not hasattr(crypto, "DEV_FERNET_KEY")


@pytest.mark.asyncio
async def test_register_byok_returns_503_without_fernet_key(authenticated_client, monkeypatch):
    monkeypatch.delenv("FERNET_KEY", raising=False)
    response = await authenticated_client.post(
        "/player/byok", json={"openrouter_api_key": "sk-or-v1-" + "a" * 64}
    )
    assert response.status_code == 503

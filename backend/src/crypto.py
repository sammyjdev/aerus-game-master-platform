"""
crypto.py - Fernet encryption for BYOK keys.

All API-key encryption and decryption operations should pass through this module.
"""
from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Return a Fernet instance created from the environment variable key."""
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError(
            'FERNET_KEY is not set. Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plaintext_key: str) -> str:
    """Encrypt an API key and return the Fernet token as UTF-8 text."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext_key.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt a stored API key.
    Raises ValueError if the token is invalid or the Fernet key is wrong.
    """
    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted_key.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt API key: invalid token")
        raise ValueError("Invalid API key or incorrect Fernet key") from exc


def generate_fernet_key() -> str:
    """Generate a new Fernet key for initial project setup."""
    return Fernet.generate_key().decode("utf-8")

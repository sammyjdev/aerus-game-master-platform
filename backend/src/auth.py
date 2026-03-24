"""
auth.py - JWT authentication and password hashing.

Invite-code authentication with long-lived JWTs and silent refresh support.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from typing import Any

from jose import JWTError, jwt

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 60 * 60 * 24 * 180  # 6 months
JWT_REFRESH_THRESHOLD = 60 * 60 * 24 * 7  # refresh when less than 7 days remain


def hash_password(password: str) -> str:
    """SHA-256 with a configured salt. Use bcrypt or argon2 in production."""
    salt = os.getenv("PASSWORD_SALT", "aerus-salt-change-me")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_token(player_id: str, username: str) -> str:
    """Create a JWT with a 6-month expiration."""
    now = time.time()
    payload = {
        "sub": player_id,
        "username": username,
        "iat": now,
        "exp": now + JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.
    Raises JWTError if the token is invalid or expired.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def should_refresh_token(token: str) -> bool:
    """Return True if the token expires in less than 7 days."""
    try:
        payload = decode_token(token)
        exp = payload.get("exp", 0)
        return (exp - time.time()) < JWT_REFRESH_THRESHOLD
    except JWTError:
        return False


def generate_invite_code() -> str:
    """Generate a secure 12-character invite code."""
    return secrets.token_urlsafe(9)

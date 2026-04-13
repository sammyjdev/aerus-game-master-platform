"""
auth.py - JWT authentication and password hashing.

Invite-code authentication with long-lived JWTs and silent refresh support.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from typing import Any

from jose import JWTError, jwt
import bcrypt

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 60 * 60 * 24 * 180  # 6 months
JWT_REFRESH_THRESHOLD = 60 * 60 * 24 * 7  # refresh when less than 7 days remain

# Bcrypt cost factor (higher = slower but more secure)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12."""
    # bcrypt.hashpw requires bytes input
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        # Handle invalid hash format
        return False


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

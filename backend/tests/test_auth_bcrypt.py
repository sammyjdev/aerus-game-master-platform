"""
test_auth_bcrypt.py — Tests for bcrypt-based password hashing (TDD for S-01).
Validates SHA-256 replacement with bcrypt as per security gap S-01.
"""
import pytest
from src.auth import hash_password, verify_password, create_token, decode_token


class TestBcryptHashing:
    """Verify bcrypt hashing replaces SHA-256."""

    def test_hash_password_returns_string(self):
        """hash_password returns a hash string."""
        pwd = "test_password_123"
        hashed = hash_password(pwd)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_not_plaintext(self):
        """Hashed password should not contain plaintext."""
        pwd = "MySecretPassword"
        hashed = hash_password(pwd)
        assert pwd not in hashed
        assert "plaintext" not in hashed.lower()

    def test_same_password_different_hash(self):
        """Two calls to hash_password with same input produce different hashes (bcrypt randomness)."""
        pwd = "test_password"
        hash1 = hash_password(pwd)
        hash2 = hash_password(pwd)
        # Bcrypt adds salt, so hashes should differ
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        pwd = "correct_password"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password returns False for incorrect password."""
        pwd = "correct_password"
        wrong_pwd = "wrong_password"
        hashed = hash_password(pwd)
        assert verify_password(wrong_pwd, hashed) is False

    def test_verify_password_empty_string(self):
        """verify_password handles empty string."""
        pwd = "password"
        hashed = hash_password(pwd)
        assert verify_password("", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Password verification is case-sensitive."""
        pwd = "MyPassword"
        hashed = hash_password(pwd)
        assert verify_password("mypassword", hashed) is False
        assert verify_password("MYPASSWORD", hashed) is False

    def test_hash_includes_bcrypt_marker(self):
        """Hash should include bcrypt marker ($2a$, $2b$, or $2y$) for validation."""
        pwd = "test_password"
        hashed = hash_password(pwd)
        # Bcrypt hashes start with $2a$, $2b$, or $2y$ (rounds marker)
        assert hashed.startswith("$2")

    def test_hash_length_bcrypt(self):
        """Bcrypt hashes are typically 60 characters."""
        pwd = "test_password"
        hashed = hash_password(pwd)
        # Bcrypt full hash is 60 chars
        assert len(hashed) == 60

    def test_jwt_still_works_after_auth_refactor(self):
        """Ensure JWT token creation and decoding still work."""
        player_id = "player-123"
        username = "testuser"
        token = create_token(player_id, username)
        decoded = decode_token(token)
        assert decoded["sub"] == player_id
        assert decoded["username"] == username

    def test_password_hash_multiple_rounds(self):
        """Verify multiple verify operations work correctly (bcrypt cost factor)."""
        pwd = "test_password"
        hashed = hash_password(pwd)
        # Call verify multiple times to ensure consistent behavior
        for _ in range(5):
            assert verify_password(pwd, hashed) is True
            assert verify_password("wrong", hashed) is False

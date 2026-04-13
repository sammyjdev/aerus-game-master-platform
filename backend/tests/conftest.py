"""
conftest.py — Shared fixtures for all tests.
"""
import os
import tempfile
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from src import state_manager
from src.auth import create_token, hash_password
from src.main import app


@pytest.fixture()
def tmp_db(tmp_path):
    """Returns a temporary database file path for test isolation."""
    db_file = tmp_path / "test_aerus.db"
    return str(db_file)


@pytest_asyncio.fixture()
async def db(tmp_db, monkeypatch):
    """
    Initializes temp database and returns an open connection.
    Ensures complete test isolation.
    """
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    await state_manager.init_db()
    async with state_manager.db_context() as conn:
        yield conn


# Test data fixtures
@pytest.fixture()
def player_id():
    """Generate a test player ID."""
    return str(uuid.uuid4())


@pytest.fixture()
def username():
    """Generate a test username."""
    return f"testuser_{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def password():
    """Generate a test password."""
    return "test_password_123"


@pytest.fixture()
def admin_secret():
    """Admin secret for testing admin routes."""
    return "test_admin_secret_key"


# FastAPI test clients
@pytest_asyncio.fixture()
async def client(tmp_db, monkeypatch):
    """
    Returns an AsyncClient for testing. No authentication.
    """
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    await state_manager.init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture()
async def authenticated_client(tmp_db, monkeypatch, player_id, username, password, admin_secret):
    """
    Returns an AsyncClient with a valid JWT token.
    Creates player and character in test DB.
    """
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    monkeypatch.setenv("ADMIN_SECRET", admin_secret)
    await state_manager.init_db()

    # Create player in DB
    async with state_manager.db_context() as conn:
        password_hash = hash_password(password)
        await state_manager.create_player(conn, player_id, username, password_hash)

    # Create token
    token = create_token(player_id, username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac


@pytest_asyncio.fixture()
async def admin_client(tmp_db, monkeypatch, admin_secret):
    """
    Returns an AsyncClient with X-Admin-Secret header set.
    """
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    monkeypatch.setenv("ADMIN_SECRET", admin_secret)
    await state_manager.init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"X-Admin-Secret": admin_secret})
        yield ac

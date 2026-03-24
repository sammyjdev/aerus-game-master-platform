"""
conftest.py — Fixtures compartilhadas para todos os testes.
"""
import os
import tempfile

import pytest
import pytest_asyncio

from src import state_manager


@pytest.fixture()
def tmp_db(tmp_path):
    """Retorna um caminho temporário para o banco de dados de teste."""
    db_file = tmp_path / "test_aerus.db"
    return str(db_file)


@pytest_asyncio.fixture()
async def db(tmp_db, monkeypatch):
    """
    Inicializa o banco de dados em arquivo temporário e retorna uma conexão aberta.
    Garante isolamento total entre testes.
    """
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    await state_manager.init_db()
    async with state_manager.db_context() as conn:
        yield conn

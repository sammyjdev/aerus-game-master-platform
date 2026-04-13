from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src import local_llm


@pytest.mark.asyncio
async def test_generate_text_uses_openrouter_first():
    """Default mode (AERUS_LOCAL_ONLY unset) uses OpenRouter, not Ollama."""
    with patch("src.local_llm._generate_with_ollama", new=AsyncMock(return_value="ok-local")) as mock_local:
        with patch("src.local_llm._generate_with_openrouter", new=AsyncMock(return_value="ok-remote")) as mock_remote:
            result = await local_llm.generate_text("sys", "usr")

    assert result == "ok-remote"
    mock_remote.assert_awaited_once()
    mock_local.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_text_fallbacks_when_not_local_only(monkeypatch):
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "false")

    with patch("src.local_llm._generate_with_ollama", new=AsyncMock(side_effect=RuntimeError("down"))):
        with patch("src.local_llm._generate_with_openrouter", new=AsyncMock(return_value="ok-fallback")) as mock_remote:
            result = await local_llm.generate_text("sys", "usr")

    assert result == "ok-fallback"
    mock_remote.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_text_raises_in_local_only(monkeypatch):
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "true")

    with patch("src.local_llm._generate_with_ollama", new=AsyncMock(side_effect=RuntimeError("down"))):
        with patch("src.local_llm._generate_with_openrouter", new=AsyncMock(return_value="should-not-use")):
            with pytest.raises(RuntimeError, match="AERUS_LOCAL_ONLY=true"):
                await local_llm.generate_text("sys", "usr")


@pytest.mark.asyncio
async def test_generate_chat_uses_openrouter_first():
    """Default mode (AERUS_LOCAL_ONLY unset) uses OpenRouter for chat, not Ollama."""
    messages = [{"role": "user", "content": "teste"}]
    with patch("src.local_llm._generate_chat_with_ollama", new=AsyncMock(return_value="ok-chat-local")) as mock_local:
        with patch("src.local_llm._generate_chat_with_openrouter", new=AsyncMock(return_value="ok-chat-remote")) as mock_remote:
            result = await local_llm.generate_chat(messages)

    assert result == "ok-chat-remote"
    mock_remote.assert_awaited_once()
    mock_local.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_chat_raises_in_local_only(monkeypatch):
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "true")
    messages = [{"role": "user", "content": "teste"}]
    with patch("src.local_llm._generate_chat_with_ollama", new=AsyncMock(side_effect=RuntimeError("down"))):
        with pytest.raises(RuntimeError, match="AERUS_LOCAL_ONLY=true"):
            await local_llm.generate_chat(messages)

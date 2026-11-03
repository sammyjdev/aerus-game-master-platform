from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.mark.asyncio
async def test_generate_chat_uses_exllamav3_when_configured(monkeypatch):
    monkeypatch.setenv("AERUS_LLM_PROVIDER", "exllamav3")
    messages = [{"role": "user", "content": "test"}]
    with patch("src.local_llm._generate_chat_with_exllamav3", new=AsyncMock(return_value="ok-exllama")) as mock_local:
        result = await local_llm.generate_chat(messages)

    assert result == "ok-exllama"
    mock_local.assert_awaited_once_with(messages, max_tokens=2048, model_override=None)


def test_provider_selection_alone_activates_local_only_and_mode(monkeypatch):
    monkeypatch.setenv("AERUS_LLM_PROVIDER", "exllamav3")
    monkeypatch.delenv("AERUS_LOCAL_ONLY", raising=False)
    assert local_llm.is_local_only() is True
    assert local_llm.configured_execution_mode() == "exllamav3-only"
    assert local_llm.configured_hosted_model() is None
    assert local_llm.configured_model_label() == "UnslopNemo-12B-v4.1-exl3-4.25bpw"


@pytest.mark.asyncio
async def test_generate_text_exllamav3_does_not_fall_through_to_openrouter(monkeypatch):
    monkeypatch.setenv("AERUS_LLM_PROVIDER", "exllamav3")
    monkeypatch.setenv("AERUS_LOCAL_ONLY", "false")
    with patch("src.local_llm._generate_with_exllamav3", new=AsyncMock(side_effect=RuntimeError("exllama connection refused"))) as mock_exllama:
        with patch("src.local_llm._generate_with_openrouter", new=AsyncMock(return_value="should-not-reach")) as mock_remote:
            with pytest.raises(RuntimeError, match="ExLlamaV3"):
                await local_llm.generate_text("sys", "usr")
    mock_exllama.assert_awaited_once()
    mock_remote.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_llm_uses_exllamav3_model_without_ollama_override(monkeypatch):
    from src import game_master
    monkeypatch.setenv("AERUS_LLM_PROVIDER", "exllamav3")
    monkeypatch.setenv("AERUS_EXLLAMAV3_MODEL", "custom-exllama-model")
    monkeypatch.setenv("AERUS_OLLAMA_GM_MODEL", "qwen2.5:14b-instruct")

    messages = [{"role": "user", "content": "hello"}]
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Narration text"
    
    async def mock_stream_gen():
        yield mock_chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_gen())

    async def mock_broadcast(gen, campaign_id=None):
        async for _ in gen:
            pass
        return "Narration text"

    with patch("src.local_llm.get_exllamav3_client", return_value=mock_client):
        with patch("src.game_master.cm.manager.broadcast_stream", side_effect=mock_broadcast):
            full_resp, narrative = await game_master._stream_llm(None, messages, campaign_id="camp1")
            assert full_resp == "Narration text"
            assert narrative == "Narration text"
            mock_client.chat.completions.create.assert_awaited_once_with(
                model="custom-exllama-model",
                messages=messages,
                stream=True,
                max_tokens=2048,
            )


@pytest.mark.asyncio
async def test_exllamav3_transport_client_boundary(monkeypatch):
    monkeypatch.setenv("AERUS_EXLLAMAV3_URL", "http://127.0.0.1:5000/v1")
    monkeypatch.setenv("AERUS_EXLLAMAV3_API_KEY", "test-secret-key")
    monkeypatch.setenv("AERUS_EXLLAMAV3_MODEL", "model-exllama-test")
    monkeypatch.setenv("AERUS_EXLLAMAV3_TIMEOUT_SECONDS", "45")

    fake_choice = SimpleNamespace(message=SimpleNamespace(content="ExLlama response text"))
    fake_response = SimpleNamespace(choices=[fake_choice])

    created_client = None

    class MockAsyncOpenAI:
        def __init__(self, api_key=None, base_url=None, timeout=None):
            nonlocal created_client
            self.api_key = api_key
            self.base_url = base_url
            self.timeout = timeout
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=fake_response)))
            created_client = self

    monkeypatch.setattr(local_llm, "AsyncOpenAI", MockAsyncOpenAI)

    messages = [{"role": "user", "content": "Hello ExLlama"}]
    result = await local_llm._generate_chat_with_exllamav3(messages, max_tokens=512)

    assert result == "ExLlama response text"
    assert created_client.api_key == "test-secret-key"
    assert created_client.base_url == "http://127.0.0.1:5000/v1"
    assert created_client.timeout == 45.0
    created_client.chat.completions.create.assert_awaited_once_with(
        model="model-exllama-test",
        messages=messages,
        max_tokens=512,
    )

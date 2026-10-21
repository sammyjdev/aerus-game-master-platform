from __future__ import annotations

import logging
import os

import httpx
from openai import AsyncOpenAI

from .application.billing.billing_router import select_billing_config
from .debug_tools import clip_text, log_debug, log_flow

logger = logging.getLogger(__name__)


def _ollama_url() -> str:
    return os.getenv("AERUS_OLLAMA_URL", "http://localhost:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("AERUS_OLLAMA_MODEL", "qwen2.5:14b-instruct")


def _exllamav3_url() -> str:
    return os.getenv("AERUS_EXLLAMAV3_URL", "http://127.0.0.1:5000/v1").rstrip("/")


def _exllamav3_model() -> str:
    return os.getenv("AERUS_EXLLAMAV3_MODEL", "UnslopNemo-12B-v4.1-exl3-4.25bpw")


def _uses_exllamav3() -> bool:
    return os.getenv("AERUS_LLM_PROVIDER", "").strip().lower() in {"exllamav3", "exllama-v3", "exllama_v3"}


def _is_local_only() -> bool:
    return os.getenv("AERUS_LOCAL_ONLY", "false").strip().lower() in {"1", "true", "yes", "on"}


def is_local_only() -> bool:
    return _is_local_only() or _uses_exllamav3()


def configured_execution_mode() -> str:
    if _uses_exllamav3():
        return "exllamav3-only"
    return "ollama-only" if _is_local_only() else "openrouter-first"


def configured_hosted_model(tension_level: int = 5) -> str | None:
    if _is_local_only() or _uses_exllamav3():
        return None
    try:
        return select_billing_config(tension_level=tension_level).model
    except Exception:
        return None


def configured_model_label(tension_level: int = 5) -> str:
    if _uses_exllamav3():
        return _exllamav3_model()
    hosted = configured_hosted_model(tension_level=tension_level)
    return hosted or _ollama_model()


def _ollama_timeout_seconds() -> float:
    try:
        return float(os.getenv("AERUS_OLLAMA_TIMEOUT_SECONDS", "3"))
    except ValueError:
        return 3.0


def _exllamav3_timeout_seconds() -> float:
    try:
        return float(os.getenv("AERUS_EXLLAMAV3_TIMEOUT_SECONDS", "60"))
    except ValueError:
        return 60.0


async def generate_text(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 220,
    model_override: str | None = None,
) -> str:
    if _uses_exllamav3():
        try:
            exllama_override = model_override if (model_override and not any(model_override.startswith(p) for p in ("qwen", "phi", "llama"))) else None
            return await _generate_with_exllamav3(
                system_prompt, user_prompt, max_tokens=max_tokens, model_override=exllama_override
            )
        except Exception as exc:
            raise RuntimeError(f"ExLlamaV3 text generation failed: {exc}") from exc

    if _is_local_only() or model_override:
        try:
            return await _generate_with_ollama(
                system_prompt,
                user_prompt,
                max_tokens=max_tokens,
                model_override=model_override,
            )
        except Exception as exc:
            if _is_local_only():
                raise RuntimeError(f"Local model failed while AERUS_LOCAL_ONLY=true: {exc}") from exc
            logger.warning("Ollama failed (model_override=%s), falling back to OpenRouter: %s", model_override, exc)

    try:
        return await _generate_with_openrouter(system_prompt, user_prompt, max_tokens=max_tokens)
    except Exception as hosted_exc:
        logger.warning("OpenRouter unavailable, falling back to Ollama: %s", hosted_exc)
        return await _generate_with_ollama(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            model_override=model_override,
        )


async def generate_chat(
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    model_override: str | None = None,
) -> str:
    if _uses_exllamav3():
        try:
            exllama_override = model_override if (model_override and not any(model_override.startswith(p) for p in ("qwen", "phi", "llama"))) else None
            return await _generate_chat_with_exllamav3(
                messages, max_tokens=max_tokens, model_override=exllama_override
            )
        except Exception as exc:
            raise RuntimeError(f"ExLlamaV3 chat generation failed: {exc}") from exc

    if _is_local_only():
        try:
            return await _generate_chat_with_ollama(
                messages,
                max_tokens=max_tokens,
                model_override=model_override,
            )
        except Exception as exc:
            raise RuntimeError(f"Local chat failed while AERUS_LOCAL_ONLY=true: {exc}") from exc

    try:
        return await _generate_chat_with_openrouter(messages, max_tokens=max_tokens)
    except Exception as hosted_exc:
        logger.warning("OpenRouter chat unavailable, falling back to Ollama: %s", hosted_exc)
        return await _generate_chat_with_ollama(
            messages,
            max_tokens=max_tokens,
            model_override=model_override,
        )



async def _generate_with_ollama(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 220,
    model_override: str | None = None,
) -> str:
    prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"
    payload = {
        "model": model_override or _ollama_model(),
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    timeout = _ollama_timeout_seconds()
    log_debug(
        logger,
        "ollama_generate_start",
        model=payload["model"],
        timeout=timeout,
        prompt_preview=clip_text(prompt, 180),
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{_ollama_url()}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    text = (data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty response")
    log_flow(logger, "ollama_generate_complete", model=payload["model"], response_chars=len(text))
    return text


async def _generate_chat_with_ollama(
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    model_override: str | None = None,
) -> str:
    payload = {
        "model": model_override or _ollama_model(),
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    timeout = _ollama_timeout_seconds() * 4
    log_debug(logger, "ollama_chat_start", model=payload["model"], timeout=timeout, messages=len(messages))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{_ollama_url()}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    message = data.get("message") or {}
    text = (message.get("content") or "").strip()
    if not text:
        raise RuntimeError("Ollama chat returned an empty response")
    log_flow(logger, "ollama_chat_complete", model=payload["model"], response_chars=len(text))
    return text


async def _generate_with_exllamav3(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 220,
    model_override: str | None = None,
) -> str:
    return await _generate_chat_with_exllamav3(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        model_override=model_override,
    )


def get_exllamav3_client() -> AsyncOpenAI:
    timeout = _exllamav3_timeout_seconds()
    return AsyncOpenAI(
        api_key=os.getenv("AERUS_EXLLAMAV3_API_KEY", "cc0bdef6b1a589e63dfe207dcb81055d"),
        base_url=_exllamav3_url(),
        timeout=timeout,
    )


async def _generate_chat_with_exllamav3(
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    model_override: str | None = None,
) -> str:
    timeout = _exllamav3_timeout_seconds()
    client = get_exllamav3_client()
    model = model_override or _exllamav3_model()
    log_debug(logger, "exllamav3_chat_start", model=model, timeout=timeout, messages=len(messages))

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("ExLlamaV3 returned an empty response")
    log_flow(logger, "exllamav3_chat_complete", model=model, response_chars=len(text))
    return text


async def _generate_with_openrouter(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 220,
    model_override: str | None = None,
) -> str:
    billing = select_billing_config(tension_level=5)
    model = model_override or os.getenv("AERUS_OPENROUTER_MODEL") or billing.model
    log_debug(logger, "openrouter_generate_start", model=model, max_tokens=max_tokens)
    client = AsyncOpenAI(api_key=billing.api_key, base_url=billing.base_url)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": "https://aerus-rpg.fly.dev",
            "X-Title": "Aerus Game Master Platform",
        },
    )
    text = (response.choices[0].message.content or "").strip()
    log_flow(logger, "openrouter_generate_complete", model=model, response_chars=len(text))
    return text


async def _generate_chat_with_openrouter(
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    model_override: str | None = None,
) -> str:
    billing = select_billing_config(tension_level=5)
    model = model_override or os.getenv("AERUS_OPENROUTER_MODEL") or billing.model
    log_debug(logger, "openrouter_chat_start", model=model, max_tokens=max_tokens, messages=len(messages))
    client = AsyncOpenAI(api_key=billing.api_key, base_url=billing.base_url)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": "https://aerus-rpg.fly.dev",
            "X-Title": "Aerus Game Master Platform",
        },
    )
    text = (response.choices[0].message.content or "").strip()
    log_flow(logger, "openrouter_chat_complete", model=model, response_chars=len(text))
    return text

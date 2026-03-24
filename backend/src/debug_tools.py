from __future__ import annotations

import json
import logging
import os
from typing import Any


def is_debug_enabled() -> bool:
    return os.getenv("AERUS_DEBUG", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _resolve_log_level() -> int:
    configured = os.getenv("AERUS_LOG_LEVEL")
    if configured:
        level = getattr(logging, configured.strip().upper(), None)
        if isinstance(level, int):
            return level
    return logging.DEBUG if is_debug_enabled() else logging.INFO


def configure_logging() -> None:
    logging.basicConfig(
        level=_resolve_log_level(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


def clip_text(value: str | None, limit: int = 160) -> str:
    text = (value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def mask_secret(value: str | None, prefix: int = 6, suffix: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= prefix + suffix:
        return "*" * len(value)
    return f"{value[:prefix]}...{value[-suffix:]}"


def summarize_payload(value: Any, max_items: int = 6) -> Any:
    if isinstance(value, str):
        return clip_text(value)
    if isinstance(value, dict):
        summary: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                summary["..."] = f"+{len(value) - max_items} keys"
                break
            summary[str(key)] = summarize_payload(item, max_items=max_items)
        return summary
    if isinstance(value, list):
        if len(value) <= max_items:
            return [summarize_payload(item, max_items=max_items) for item in value]
        return [
            *[summarize_payload(item, max_items=max_items) for item in value[:max_items]],
            f"... +{len(value) - max_items} items",
        ]
    return value


def _serialize_fields(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        parts.append(
            f"{key}={json.dumps(summarize_payload(value), ensure_ascii=False)}"
        )
    return " ".join(parts)


def log_flow(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = _serialize_fields(fields)
    if payload:
        logger.info("event=%s %s", event, payload)
        return
    logger.info("event=%s", event)


def log_debug(logger: logging.Logger, event: str, **fields: Any) -> None:
    if not is_debug_enabled():
        return
    payload = _serialize_fields(fields)
    if payload:
        logger.debug("event=%s %s", event, payload)
        return
    logger.debug("event=%s", event)
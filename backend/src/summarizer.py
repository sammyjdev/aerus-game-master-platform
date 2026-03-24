from __future__ import annotations

import os

import aiosqlite

from . import state_manager
from .local_llm import generate_text


async def summarize_recent_history(conn: aiosqlite.Connection, limit: int = 12) -> str:
    history = await state_manager.get_recent_history(conn, limit=limit)
    if not history:
        return ""

    transcript = "\n".join(
        f"{('Players' if row['role'] == 'user' else 'GM')}: {row['content']}"
        for row in history
    )
    system_prompt = (
        "You are an RPG summarizer. "
        "Summarize permanent facts and consequences in up to 6 short lines in English. "
        "Do not invent facts."
    )
    user_prompt = (
        "Summarize the turns below focusing on state changes, open threats, "
        "objectives, and narrative hooks.\n\n"
        f"{transcript}"
    )
    summary_model = os.getenv("AERUS_OLLAMA_SUMMARIZER_MODEL")
    return await generate_text(
        system_prompt,
        user_prompt,
        max_tokens=220,
        model_override=summary_model,
    )

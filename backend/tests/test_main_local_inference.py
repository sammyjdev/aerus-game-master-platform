from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.main import _infer_class_from_backstory_local


@pytest.mark.asyncio
async def test_local_backstory_inference_uses_structured_output():
    with patch(
        "src.main.generate_text",
        new=AsyncMock(return_value='{"inferred_class":"Ranger","rationale":"perfil de caÃ§a"}'),
    ):
        inferred = await _infer_class_from_backstory_local(
            "Passei anos caÃ§ando monstros nas florestas geladas.",
            "guild_of_threads",
        )

    assert inferred == "Ranger"


@pytest.mark.asyncio
async def test_local_backstory_inference_fallbacks_to_keyword_when_invalid_json():
    with patch("src.main.generate_text", new=AsyncMock(return_value="not-json")):
        inferred = await _infer_class_from_backstory_local(
            "Treinei com espada e vivi em batalhas constantes.",
            "empire_valdrek",
        )

    assert inferred == "Soldier"


"""
ws_contracts.py — Pydantic schemas for all outgoing WebSocket messages.

These schemas serve as the single source of truth for the WS message contract.
All broadcast/send calls in connection_manager and game_master should produce
payloads that conform to these types.

The frontend Zod schemas in frontend/src/types/wsSchemas.ts must mirror this file.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Narrative ────────────────────────────────────────────────────────────────

class NarrativeTokenMessage(BaseModel):
    type: Literal["narrative_token"]
    token: str


class StreamEndMessage(BaseModel):
    type: Literal["stream_end"]


class GmThinkingMessage(BaseModel):
    type: Literal["gm_thinking"]
    message: str


# ── Game State ───────────────────────────────────────────────────────────────

class GameEventMessage(BaseModel):
    type: Literal["game_event"]
    event: str
    payload: dict[str, Any]


class StateUpdateMessage(BaseModel):
    type: Literal["state_update"]
    delta: dict[str, Any]


class FullStateSyncMessage(BaseModel):
    type: Literal["full_state_sync"]
    state: dict[str, Any]
    world_state: dict[str, Any] | None = None


class HistorySyncMessage(BaseModel):
    type: Literal["history_sync"]
    entries: list[dict[str, Any]]


# ── Dice ─────────────────────────────────────────────────────────────────────

class DiceRollMessage(BaseModel):
    type: Literal["dice_roll"]
    player: str
    die: int = Field(gt=0)
    purpose: str
    result: int
    is_critical: bool = False
    is_fumble: bool = False


class RequestDiceRollMessage(BaseModel):
    type: Literal["request_dice_roll"]
    roll_id: str
    roll_type: str
    dc: int
    description: str


class DiceRollResolvedMessage(BaseModel):
    type: Literal["dice_roll_resolved"]
    roll_id: str
    verdict: Literal["accept_with_bonus", "accept_no_bonus", "reject", "reroll_requested"]
    circumstance_bonus: int
    final_result: int | None
    explanation: str


# ── Audio / Media ────────────────────────────────────────────────────────────

class AudioCueMessage(BaseModel):
    type: Literal["audio_cue"]
    cue: str


class BossMusicMessage(BaseModel):
    type: Literal["boss_music"]
    url: str | None = None
    tension_level: int | None = None
    intensity: Literal["high", "medium"] | None = None


class ImageReadyMessage(BaseModel):
    type: Literal["image_ready"]
    url: str
    subject: str


# ── Auth ─────────────────────────────────────────────────────────────────────

class TokenRefreshMessage(BaseModel):
    type: Literal["token_refresh"]
    access_token: str


# ── Isekai ───────────────────────────────────────────────────────────────────

class IsekaiConvocationMessage(BaseModel):
    type: Literal["isekai_convocation"]
    faction: str
    narrative: str
    secret_objective: str


class FactionObjectiveUpdateMessage(BaseModel):
    type: Literal["faction_objective_update"] = "faction_objective_update"
    faction: str
    objective: str
    status: Literal["in_progress", "completed", "failed"]
    cred_change: float


class DiceResultMessage(BaseModel):
    type: Literal["dice_result"] = "dice_result"
    player_id: str
    die: int = Field(gt=0)
    result: int


# ── Errors ───────────────────────────────────────────────────────────────────

class ErrorMessage(BaseModel):
    type: Literal["error"]
    message: str


class MilestoneMessage(BaseModel):
    type: Literal["milestone"] = "milestone"
    player_id: str
    milestones: list[str]


# ── Church Seals ─────────────────────────────────────────────────────────────

class SealEventMessage(BaseModel):
    type: Literal["seal_event"] = "seal_event"
    player_id: str
    action: Literal["granted", "revoked"]
    seal_type: str | None


# ── Union type for all outgoing messages ─────────────────────────────────────

OutgoingWSMessage = (
    NarrativeTokenMessage
    | StreamEndMessage
    | GmThinkingMessage
    | GameEventMessage
    | StateUpdateMessage
    | FullStateSyncMessage
    | HistorySyncMessage
    | DiceRollMessage
    | RequestDiceRollMessage
    | DiceRollResolvedMessage
    | AudioCueMessage
    | BossMusicMessage
    | ImageReadyMessage
    | TokenRefreshMessage
    | IsekaiConvocationMessage
    | FactionObjectiveUpdateMessage
    | DiceResultMessage
    | MilestoneMessage
    | SealEventMessage
    | ErrorMessage
)

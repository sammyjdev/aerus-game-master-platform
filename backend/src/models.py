"""
Dataclasses and Pydantic models - contracts between modules.
No module should use raw dictionaries for internal communication when a model fits.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel


class Faction(str, Enum):
    CHURCH_PURE_FLAME = "church_pure_flame"
    EMPIRE_VALDREK = "empire_valdrek"
    GUILD_OF_THREADS = "guild_of_threads"
    CHILDREN_OF_BROKEN_THREAD = "children_of_broken_thread"


class Race(str, Enum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALF_ELF = "half-elf"
    CORRUPTED = "corrupted"


class Subrace(str, Enum):
    HUMAN_NORTHERNER = "human_northerner"
    HUMAN_TRADER = "human_trader"
    HUMAN_KHORATHI = "human_khorathi"
    HUMAN_DAWNMERE = "human_dawnmere"
    ELF_TWILIGHT = "elf_twilight"
    ELF_CORRUPTED_FAE = "elf_corrupted_fae"
    ELF_MIST = "elf_mist"
    ELF_WANDERING_FAE = "elf_wandering_fae"
    FORGER_STONE_GOLIATH = "forger_stone_goliath"
    FORGER_DEEP_DWARF = "forger_deep_dwarf"
    FORGER_STENVAARD = "forger_stenvaard"


class Element(str, Enum):
    WATER = "water"
    EARTH = "earth"
    FIRE = "fire"
    AIR = "air"
    ENERGY = "energy"
    SPIRIT = "spirit"


class WeaponType(str, Enum):
    SWORD = "sword"
    AXE = "axe"
    BOW = "bow"
    STAFF = "staff"
    DAGGER = "dagger"
    SPEAR = "spear"
    SHIELD = "shield"
    UNARMED = "unarmed"


class ItemRarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class PlayerStatus(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    SPECTATOR = "spectator"


class GameEventType(str, Enum):
    DEATH = "DEATH"
    LEVELUP = "LEVELUP"
    BOSS_PHASE = "BOSS_PHASE"
    BOSS_DEFEATED = "BOSS_DEFEATED"
    LOOT = "LOOT"
    MILESTONE = "MILESTONE"
    CLASS_MUTATION = "CLASS_MUTATION"
    FACTION_CONFLICT = "FACTION_CONFLICT"
    COOP_MISSION = "COOP_MISSION"
    REPUTATION_CHANGE = "REPUTATION_CHANGE"
    ABILITY_UNLOCK = "ABILITY_UNLOCK"


@dataclass
class Attributes:
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    vitality: int = 10
    luck: int = 10
    charisma: int = 10

    def total(self) -> int:
        return (
            self.strength
            + self.dexterity
            + self.intelligence
            + self.vitality
            + self.luck
            + self.charisma
        )


@dataclass
class Character:
    player_id: str
    name: str
    race: Race
    faction: Faction
    backstory: str
    attributes: Attributes = field(default_factory=Attributes)
    inferred_class: str = "Unknown"
    level: int = 1
    experience: int = 0
    max_hp: int = 100
    current_hp: int = 100
    status: PlayerStatus = PlayerStatus.ALIVE
    secret_objective: str = ""
    contribution_score: float = 0.0
    magic_proficiency: dict[str, int] = field(default_factory=dict)
    weapon_proficiency: dict[str, int] = field(default_factory=dict)
    passive_milestones: list[str] = field(default_factory=list)
    # Skills: organic progression tracked per sub-skill key
    # Format: {"skill_key": {"rank": int, "uses": int, "impact": float}}
    skills: dict[str, dict] = field(default_factory=dict)
    attribute_points_available: int = 0
    proficiency_points_available: int = 0
    subrace: str | None = None


@dataclass
class PlayerAction:
    player_id: str
    player_name: str
    action_text: str
    timestamp: float


@dataclass
class ActionBatch:
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: list[PlayerAction] = field(default_factory=list)
    turn_number: int = 0


@dataclass
class ContextLayers:
    """Four-layer context engineering output."""

    l0_static: str
    l1_campaign: str
    l2_state: str
    l3_history: str
    memory_injection: str
    lore_retrieval: str

    def to_system_prompt(self) -> str:
        parts = [
            "# WORLD: AERUS",
            self.l0_static,
            "# CURRENT CAMPAIGN",
            self.l1_campaign,
            "# CURRENT STATE",
            self.l2_state,
            "# GM MEMORY",
            self.memory_injection,
            "# RELEVANT LORE",
            self.lore_retrieval,
        ]
        return "\n\n".join(p for p in parts if p.strip())


@dataclass
class GMResponse:
    """Parsed response from the LLM Game Master."""

    narrative: str
    dice_rolls: list[dict[str, Any]] = field(default_factory=list)
    state_delta: dict[str, Any] = field(default_factory=dict)
    game_events: list[dict[str, Any]] = field(default_factory=list)
    tension_level: int = 5
    audio_cue: str | None = None
    image_prompt: str | None = None


@dataclass
class MemoryLayers:
    character: str = ""
    world: str = ""
    arc: str = ""


@dataclass
class FactionReputation:
    """A player's reputation with a specific faction."""

    player_id: str
    faction_id: str
    score: int = 0

    @property
    def label(self) -> str:
        if self.score <= -50:
            return "Enemy"
        if self.score <= -20:
            return "Hostile"
        if self.score < 20:
            return "Neutral"
        if self.score < 50:
            return "Friendly"
        return "Allied"


@dataclass
class LoreResult:
    documents: list[str] = field(default_factory=list)
    metadatas: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InviteCode:
    code: str
    created_by: str
    used: bool = False
    used_by: str | None = None


class RedeemInviteRequest(BaseModel):
    invite_code: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateCharacterRequest(BaseModel):
    name: str
    race: Race
    faction: Faction
    backstory: str
    subrace: str | None = None


class AnalyzeBackstoryRequest(BaseModel):
    backstory: str


class SpendAttributePointsRequest(BaseModel):
    attribute: str  # strength | dexterity | intelligence | vitality | luck | charisma
    target_value: int


class SpendProficiencyPointsRequest(BaseModel):
    prof_type: str  # "weapon" | "magic"
    key: str        # e.g. "sword", "fire"
    target_rank: int


class PlayerActionRequest(BaseModel):
    action: str


class RegisterByokKeyRequest(BaseModel):
    openrouter_api_key: str


class DiceRollRequestBody(BaseModel):
    player_id: str
    roll_type: str
    dc: int
    description: str


class DiceRollSubmitBody(BaseModel):
    roll_id: str
    initial_roll: int
    initial_result: int
    argument: str = ""


class DiceRollResolveBody(BaseModel):
    roll_id: str
    verdict: str
    circumstance_bonus: int = 0
    explanation: str = ""


class UpdateBackstoryBody(BaseModel):
    backstory: str


class UpdateMacrosBody(BaseModel):
    macros: list[dict[str, str]]


class UpdateSpellAliasesBody(BaseModel):
    aliases: dict[str, str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CharacterResponse(BaseModel):
    player_id: str
    name: str
    race: str
    faction: str
    inferred_class: str
    level: int
    attributes: dict[str, int]
    status: str
    secret_objective: str | None = None


class WSMessageType(str, Enum):
    # Server → client: narrative
    NARRATIVE_TOKEN = "narrative_token"
    STREAM_END = "stream_end"
    GM_THINKING = "gm_thinking"
    # Server → client: game state
    GAME_EVENT = "game_event"
    STATE_UPDATE = "state_update"
    FULL_STATE_SYNC = "full_state_sync"
    HISTORY_SYNC = "history_sync"
    # Server → client: dice
    DICE_ROLL = "dice_roll"
    REQUEST_DICE_ROLL = "request_dice_roll"
    DICE_ROLL_RESOLVED = "dice_roll_resolved"
    # Server → client: audio/media
    AUDIO_CUE = "audio_cue"
    BOSS_MUSIC = "boss_music"
    IMAGE_READY = "image_ready"
    # Server → client: auth
    TOKEN_REFRESH = "token_refresh"
    # Server → client: isekai
    ISEKAI_CONVOCATION = "isekai_convocation"
    FACTION_OBJECTIVE_UPDATE = "faction_objective_update"
    # Server → client: errors
    ERROR = "error"

"""
gm_eval.py â€” Script de avaliaÃ§Ã£o de comportamento do GM do Aerus RPG.

Testa o modelo Ollama contra cenÃ¡rios prÃ©-definidos e imprime um relatÃ³rio
estruturado com assertions automÃ¡ticas + narrativa completa para avaliaÃ§Ã£o
subjetiva.

Uso:
    cd backend && .venv/Scripts/python eval/gm_eval.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import io
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ForÃ§a UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

import aiosqlite

# Garante que backend/src estÃ¡ no path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Timeout generoso para o modelo 14B local (resposta GM pode levar ~60-120s)
os.environ.setdefault("AERUS_OLLAMA_TIMEOUT_SECONDS", "120")
# ForÃ§a uso local â€” sem fallback para OpenRouter no eval
os.environ.setdefault("AERUS_LOCAL_ONLY", "true")

from src import state_manager, vector_store
from src.context_builder import build_context, build_gm_system_prompt
from src.local_llm import _ollama_model, generate_chat
from src.models import ActionBatch, PlayerAction

# ---------------------------------------------------------------------------
# Constantes visuais
# ---------------------------------------------------------------------------

LINE = "=" * 60
THIN = "â”€" * 57
PASS = "âœ…"
FAIL = "âŒ"


def _history_file_path() -> Path:
    default_path = Path(__file__).parent / "history" / "gm_eval_runs.jsonl"
    env_path = os.getenv("AERUS_EVAL_HISTORY_FILE", "").strip()
    if env_path:
        return Path(env_path)
    return default_path


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Assertion:
    """Uma verificaÃ§Ã£o sobre a resposta do GM."""
    label: str
    fn: Any  # callable(narrative: str, game_state: dict) -> bool


@dataclass
class ScenarioSetup:
    """ConfiguraÃ§Ã£o de DB para um cenÃ¡rio."""
    num_players: int = 1
    level: int = 1
    hp_fraction: float = 1.0       # 1.0 = HP cheio
    location: str = "Porto Myr"
    tension: int = 3
    coop_mission_active: bool = False
    coop_mission_completed: bool = False
    inferred_class: str = "Guerreiro"
    faction: str = "guild_of_threads"
    extra_level: int | None = None  # segundo player (se num_players=2)
    extra_hp_fraction: float | None = None  # HP do 2Âº player; None = igual a hp_fraction
    extra_inferred_class: str = "Mago"  # classe do 2Âº player
    initial_inventory: list[dict[str, Any]] = field(default_factory=list)
    extra_initial_inventory: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Scenario:
    name: str
    description: str
    setup: ScenarioSetup
    action_text: str
    assertions: list[Assertion] = field(default_factory=list)
    # HistÃ³rico de turnos anteriores (para simular disputas multi-turn)
    # Formato: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history_messages: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario: Scenario
    narrative: str
    game_state: dict[str, Any]
    raw_response: str
    passed: list[str]
    failed: list[str]
    error: str | None = None
    elapsed_seconds: float = 0.0

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed)

    @property
    def score(self) -> int:
        return len(self.passed)


# ---------------------------------------------------------------------------
# InicializaÃ§Ã£o do banco em memÃ³ria
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS invites (
    code        TEXT PRIMARY KEY,
    created_by  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    used_by     TEXT,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id           TEXT PRIMARY KEY,
    username            TEXT UNIQUE NOT NULL,
    password_hash       TEXT NOT NULL,
    name                TEXT,
    race                TEXT,
    faction             TEXT,
    backstory           TEXT,
    inferred_class      TEXT DEFAULT 'Desconhecido',
    level               INTEGER NOT NULL DEFAULT 1,
    experience          INTEGER NOT NULL DEFAULT 0,
    max_hp              INTEGER NOT NULL DEFAULT 100,
    current_hp          INTEGER NOT NULL DEFAULT 100,
    max_mp              INTEGER NOT NULL DEFAULT 50,
    current_mp          INTEGER NOT NULL DEFAULT 50,
    max_stamina         INTEGER NOT NULL DEFAULT 100,
    current_stamina     INTEGER NOT NULL DEFAULT 100,
    status              TEXT NOT NULL DEFAULT 'alive',
    secret_objective    TEXT DEFAULT '',
    contribution_score  REAL NOT NULL DEFAULT 0.0,
    byok_key_encrypted  TEXT,
    created_at          REAL NOT NULL,
    attributes_json     TEXT NOT NULL DEFAULT '{}',
    magic_prof_json     TEXT NOT NULL DEFAULT '{}',
    weapon_prof_json    TEXT NOT NULL DEFAULT '{}',
    milestones_json     TEXT NOT NULL DEFAULT '[]',
    currency_json       TEXT NOT NULL DEFAULT '{"copper":0,"silver":5,"gold":0,"platinum":0}',
    inventory_weight    REAL NOT NULL DEFAULT 0.0,
    weight_capacity     REAL NOT NULL DEFAULT 80.0,
    macros_json         TEXT NOT NULL DEFAULT '[]',
    spell_aliases_json  TEXT NOT NULL DEFAULT '{}',
    backstory_changed_recently INTEGER NOT NULL DEFAULT 0,
    convocation_sent    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    player_id   TEXT NOT NULL REFERENCES players(player_id),
    token_hash  TEXT NOT NULL,
    expires_at  REAL NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    item_id     TEXT PRIMARY KEY,
    player_id   TEXT NOT NULL REFERENCES players(player_id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    rarity      TEXT NOT NULL DEFAULT 'comum',
    quantity    INTEGER NOT NULL DEFAULT 1,
    equipped    INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conditions (
    condition_id    TEXT PRIMARY KEY,
    player_id       TEXT NOT NULL REFERENCES players(player_id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    duration_turns  INTEGER,
    applied_at_turn INTEGER NOT NULL,
    is_buff         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS history (
    history_id  TEXT PRIMARY KEY,
    turn_number INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id  TEXT PRIMARY KEY,
    turn_start  INTEGER NOT NULL,
    turn_end    INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quest_flags (
    flag_key    TEXT PRIMARY KEY,
    flag_value  TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS character_memory (
    player_id   TEXT PRIMARY KEY REFERENCES players(player_id),
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS arc_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_images (
    image_id    TEXT PRIMARY KEY,
    prompt      TEXT NOT NULL,
    url         TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS faction_reputation (
    player_id   TEXT NOT NULL REFERENCES players(player_id),
    faction_id  TEXT NOT NULL,
    score       INTEGER NOT NULL DEFAULT 0,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (player_id, faction_id)
);

CREATE TABLE IF NOT EXISTS dice_roll_arguments (
    roll_id              TEXT PRIMARY KEY,
    player_id            TEXT NOT NULL REFERENCES players(player_id),
    roll_type            TEXT NOT NULL,
    dc                   INTEGER NOT NULL,
    description          TEXT NOT NULL,
    initial_roll         INTEGER,
    initial_result       INTEGER,
    argument             TEXT NOT NULL DEFAULT '',
    argument_submitted   INTEGER NOT NULL DEFAULT 0,
    verdict              TEXT,
    circumstance_bonus   INTEGER NOT NULL DEFAULT 0,
    final_result         INTEGER,
    explanation          TEXT NOT NULL DEFAULT '',
    created_at           REAL NOT NULL,
    resolved_at          REAL
);

CREATE TABLE IF NOT EXISTS aerus_calendar (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);
"""


async def _init_memory_db(conn: aiosqlite.Connection) -> None:
    """Inicializa todas as tabelas num banco em memÃ³ria."""
    conn.row_factory = aiosqlite.Row
    await conn.executescript(_CREATE_TABLES_SQL)
    await conn.commit()
    # Insere world_state com valores padrÃ£o
    await state_manager.ensure_default_world_state(conn)


# ---------------------------------------------------------------------------
# Seeding de jogadores
# ---------------------------------------------------------------------------

async def _seed_player(
    conn: aiosqlite.Connection,
    name: str,
    username: str,
    level: int,
    hp_fraction: float,
    location: str,
    inferred_class: str,
    faction: str,
) -> str:
    """Insere um jogador e retorna o player_id."""
    player_id = str(uuid.uuid4())
    max_hp = 100
    current_hp = max(1, int(max_hp * hp_fraction))
    attrs = json.dumps({
        "strength": 12,
        "dexterity": 10,
        "intelligence": 10,
        "vitality": 10,
        "luck": 10,
        "charisma": 10,
    })
    now = time.time()
    await conn.execute(
        """INSERT INTO players
           (player_id, username, password_hash, name, race, faction, backstory,
            inferred_class, level, experience, max_hp, current_hp,
            status, secret_objective, created_at, attributes_json,
            magic_prof_json, weapon_prof_json, milestones_json,
            currency_json, inventory_weight, weight_capacity,
            macros_json, spell_aliases_json, backstory_changed_recently, convocation_sent)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            player_id, username, "hash", name, "humano", faction,
            "Um aventureiro convocado para Aerus.",
            inferred_class, level,
            (level - 1) * 100,  # experience simples
            max_hp, current_hp,
            "alive", "Descobrir a verdade sobre Aerus.",
            now, attrs, "{}", "{}", "[]",
            '{"copper":0,"silver":5,"gold":0,"platinum":0}',
            0.0, 80.0, "[]", "{}", 0, 0,
        ),
    )
    await conn.commit()
    return player_id


async def _seed_inventory_items(
    conn: aiosqlite.Connection,
    player_id: str,
    items: list[dict[str, Any]],
) -> None:
    """Insere itens de inventÃ¡rio iniciais para um jogador."""
    if not items:
        return

    for item in items:
        item_id = str(item.get("item_id") or uuid.uuid4())
        name = str(item.get("name") or "Item")
        description = str(item.get("description") or "")
        rarity = str(item.get("rarity") or "comum")
        quantity_raw = item.get("quantity", 1)
        quantity = int(quantity_raw) if isinstance(quantity_raw, (int, float, str)) else 1
        equipped = 1 if bool(item.get("equipped", False)) else 0
        metadata = item.get("metadata", {})
        metadata_json = json.dumps(metadata if isinstance(metadata, dict) else {})

        await conn.execute(
            """INSERT INTO inventory
               (item_id, player_id, name, description, rarity, quantity, equipped, metadata_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                item_id,
                player_id,
                name,
                description,
                rarity,
                max(1, quantity),
                equipped,
                metadata_json,
            ),
        )

    await conn.commit()


async def _set_location(conn: aiosqlite.Connection, location: str) -> None:
    await state_manager.set_world_state(conn, "current_location", location)


async def _set_tension(conn: aiosqlite.Connection, tension: int) -> None:
    await state_manager.set_world_state(conn, "tension_level", str(tension))


async def _set_coop_mission(
    conn: aiosqlite.Connection,
    active: bool,
    completed: bool,
    num_players: int,
) -> None:
    await state_manager.set_quest_flag(
        conn, state_manager.COOP_MISSION_ACTIVE_KEY, "1" if active else "0"
    )
    await state_manager.set_quest_flag(
        conn, state_manager.COOP_MISSION_COMPLETED_KEY, "1" if completed else "0"
    )
    await state_manager.set_quest_flag(
        conn, state_manager.COOP_MISSION_REQUIRED_PLAYERS_KEY, str(num_players)
    )
    await state_manager.set_quest_flag(
        conn, state_manager.COOP_MISSION_OBJECTIVE_KEY,
        state_manager.COOP_MISSION_OBJECTIVE_DEFAULT,
    )
    await state_manager.set_quest_flag(
        conn, "cooperative_mission_id", "mission_coop_intro_v1"
    )
    # Jogadores que completaram
    done = str(num_players) if completed else "0"
    await state_manager.set_quest_flag(
        conn, "cooperative_mission_completed_players", done
    )


# ---------------------------------------------------------------------------
# Parsing de resposta
# ---------------------------------------------------------------------------

def _parse_response(raw: str) -> tuple[str, dict[str, Any]]:
    """
    Separa narrativa e JSON da resposta do GM.
    Retorna (narrative, game_state_dict).
    """
    game_state: dict[str, Any] = {}

    match = re.search(r"<game_state>(.*?)</game_state>", raw, re.DOTALL)
    if match:
        json_text = match.group(1).strip()
        narrative = raw[: match.start()].strip()
        try:
            game_state = json.loads(json_text)
        except json.JSONDecodeError:
            # Remove comentÃ¡rios inline estilo JS (// ...) que o modelo Ã s vezes insere
            json_text_nocomments = re.sub(r"//[^\n]*", "", json_text)
            # Tenta limpeza bÃ¡sica de JSON malformado (trailing commas)
            json_text_clean = re.sub(r",\s*([}\]])", r"\1", json_text_nocomments)
            try:
                game_state = json.loads(json_text_clean)
            except json.JSONDecodeError:
                pass
    else:
        narrative = raw.strip()

    return narrative, game_state


# ---------------------------------------------------------------------------
# DefiniÃ§Ã£o dos cenÃ¡rios
# ---------------------------------------------------------------------------

def _build_scenarios() -> list[Scenario]:
    return [
        # ------------------------------------------------------------------
        # 1. Abertura em Porto Myr
        # ------------------------------------------------------------------
        Scenario(
            name="Abertura em Porto Myr",
            description="Jogador nÃ­vel 1 em Porto Myr, tensÃ£o baixa, missÃ£o coop ativa.",
            setup=ScenarioSetup(
                num_players=1,
                level=1,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=3,
                coop_mission_active=True,
                coop_mission_completed=False,
            ),
            action_text=(
                "Kael olha ao redor do porto, tentando entender onde estÃ¡ "
                "e por que foi convocado para este mundo."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="TensÃ£o <= 4 (ou ausente em exploraÃ§Ã£o)",
                    fn=lambda n, gs: gs.get("tension_level", 0) <= 4,
                ),
                Assertion(
                    label="Menciona Porto Myr",
                    fn=lambda n, gs: "porto myr" in n.lower() or "porto" in n.lower(),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 2. Combate com criatura Tier 1
        # ------------------------------------------------------------------
        Scenario(
            name="Combate com criatura Tier 1",
            description="Jogador nÃ­vel 3, ataca Vira-Sombra, tensÃ£o 5.",
            setup=ScenarioSetup(
                num_players=1,
                level=3,
                hp_fraction=1.0,
                location="Floresta das Cinzas",
                tension=5,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Ataco o Vira-Sombra com minha espada, mirando no pescoÃ§o."
            ),
            assertions=[
                Assertion(
                    label="dice_rolls presentes",
                    fn=lambda n, gs: bool(gs.get("dice_rolls")),
                ),
                Assertion(
                    label="hp_change negativo em algum jogador",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="Narrativa menciona combate",
                    fn=lambda n, gs: _mentions_combat(n),
                ),
                Assertion(
                    label="TensÃ£o >= 3 (combate presente, mesmo pÃ³s-vitÃ³ria)",
                    fn=lambda n, gs: gs.get("tension_level", 0) >= 3,
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 3. AÃ§Ã£o que gera reputaÃ§Ã£o
        # ------------------------------------------------------------------
        Scenario(
            name="AÃ§Ã£o que gera reputaÃ§Ã£o",
            description="Jogador nÃ­vel 5 ajuda guarda da Igreja, esperamos reputation_delta positivo.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=3,
                inferred_class="Paladino",
                faction="guild_of_threads",
            ),
            action_text=(
                "Ajudo o guarda da Igreja que foi atacado pelo ladrÃ£o, "
                "segurando o ferido enquanto chamo por ajuda."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="reputation_delta presente com faction_id de Igreja",
                    fn=lambda n, gs: _has_reputation_delta(gs, "church_pure_flame"),
                ),
                Assertion(
                    label="reputation_delta Ã© positivo",
                    fn=lambda n, gs: _has_positive_reputation_delta(gs, "church_pure_flame"),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 4. MissÃ£o cooperativa bloqueante
        # ------------------------------------------------------------------
        Scenario(
            name="MissÃ£o cooperativa bloqueante",
            description="2 jogadores nÃ­vel 2, missÃ£o coop ativa e incompleta, tentam sair de Porto Myr.",
            setup=ScenarioSetup(
                num_players=2,
                level=2,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=4,
                coop_mission_active=True,
                coop_mission_completed=False,
            ),
            action_text=(
                "Kael e Lyra decidem zarpar do porto rumo ao continente, "
                "deixando as Ilhas de Myr para trÃ¡s sem completar a missÃ£o."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="GM bloqueia saÃ­da com obstÃ¡culo concreto",
                    fn=lambda n, gs: _blocks_or_discourages_departure(n),
                ),
                Assertion(
                    label="Narrativa NÃƒO descreve partida bem-sucedida",
                    fn=lambda n, gs: _location_not_changed(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 5. Alta tensÃ£o â€” combate quase mortal
        # ------------------------------------------------------------------
        Scenario(
            name="Alta tensÃ£o â€” combate quase mortal",
            description="Jogador nÃ­vel 4, HP=5, tensÃ£o 8, tenta fugir do Golem de Cinzas.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=0.05,   # HP crÃ­tico (5/100)
                location="RuÃ­nas das Cinzas",
                tension=8,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Tento fugir do Golem de Cinzas enquanto busco qualquer cobertura."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="TensÃ£o mantida alta (>= 7)",
                    fn=lambda n, gs: gs.get("tension_level", 0) >= 7,
                ),
                Assertion(
                    label="Narrativa transmite urgÃªncia/perigo",
                    fn=lambda n, gs: _is_visceral(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 6. Trigger de ABILITY_UNLOCK (nÃ­vel 5)
        # ------------------------------------------------------------------
        Scenario(
            name="Trigger de ABILITY_UNLOCK (nÃ­vel 5)",
            description="Jogador recÃ©m ao nÃ­vel 5 tenta movimento instintivo com espada.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=4,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael tenta usar sua espada para criar uma brecha defensiva, "
                "um movimento que nunca aprendeu formalmente mas que seus "
                "instintos sugerem. (Kael acabou de atingir o nÃ­vel 5 â€” "
                "conceda o desbloqueio de habilidade ABILITY_UNLOCK agora.)"
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="game_events contÃ©m tipo ABILITY_UNLOCK exato",
                    fn=lambda n, gs: _has_event_type(gs, "ABILITY_UNLOCK"),
                ),
                Assertion(
                    label="Narrativa menciona progressÃ£o ou habilidade",
                    fn=lambda n, gs: _mentions_progression(n),
                ),
            ],
        ),
        # ------------------------------------------------------------------
        # 7. LEVELUP event
        # ------------------------------------------------------------------
        Scenario(
            name="LEVELUP event estruturado",
            description="Jogador nÃ­vel 9 ganha XP suficiente para subir ao nÃ­vel 10.",
            setup=ScenarioSetup(
                num_players=1,
                level=9,
                hp_fraction=0.6,
                location="Floresta das Cinzas",
                tension=5,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael desfere o golpe final no CÃ£o-Sombra, encerrando o combate. "
                "Este era o Ãºltimo ponto de experiÃªncia necessÃ¡rio para subir de nÃ­vel â€” "
                "Kael acaba de atingir o nÃ­vel 10. Narre a subida de nÃ­vel. "
                "No <game_state>, inclua obrigatoriamente um evento LEVELUP com new_level=10 "
                "e experience_gain positivo no state_delta."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="LEVELUP presente em game_events com new_level",
                    fn=lambda n, gs: _has_levelup_event(gs),
                ),
                Assertion(
                    label="experience_gain presente em state_delta",
                    fn=lambda n, gs: _has_experience_gain(gs),
                ),
                Assertion(
                    label="Narrativa menciona progressÃ£o",
                    fn=lambda n, gs: _mentions_progression(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 8. LOOT com estrutura completa
        # ------------------------------------------------------------------
        Scenario(
            name="LOOT com estrutura completa",
            description="Jogador nÃ­vel 7 mata chefe menor e saqueia item raro.",
            setup=ScenarioSetup(
                num_players=1,
                level=7,
                hp_fraction=0.5,
                location="RuÃ­nas das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael derrota o GuardiÃ£o Corrompido das RuÃ­nas e foueja o corpo "
                "em busca de itens. O chefe carregava uma arma ou artefato especial."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="LOOT em game_events com item name e rarity",
                    fn=lambda n, gs: _has_loot_event_with_items(gs),
                ),
                Assertion(
                    label="Item tem rarity nÃ£o-comum (raro, Ã©pico, lendÃ¡rio ou mÃ­tico)",
                    fn=lambda n, gs: _has_non_common_loot_rarity(gs),
                ),
                Assertion(
                    label="Narrativa descreve o item encontrado",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "arma", "espada", "adaga", "lÃ¢mina", "cajado", "arco", "machado",
                            "artefato", "relÃ­quia", "anel", "amuleto", "escudo", "armadura",
                            "raro", "Ã©pico", "lendÃ¡rio", "especial", "brilha", "emana",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 9. Morte do jogador (permadeath)
        # ------------------------------------------------------------------
        Scenario(
            name="Morte do jogador â€” permadeath",
            description="Jogador nÃ­vel 2 com 1 HP Ã© golpeado fatalmente pelo Golem.",
            setup=ScenarioSetup(
                num_players=1,
                level=2,
                hp_fraction=0.01,  # 1 HP
                location="RuÃ­nas das Cinzas",
                tension=9,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael tenta bloquear o golpe massivo do Golem de Cinzas, "
                "mas estÃ¡ Ã  beira do colapso com apenas 1 HP. O golpe o acerta em cheio â€” "
                "Ã© fatal, Kael morre. No <game_state>, inclua obrigatoriamente "
                'um evento DEATH em game_events com \'cause\': \'Golpe do Golem de Cinzas\'.'
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="DEATH presente em game_events com cause",
                    fn=lambda n, gs: _has_death_event_or_fatal_state(gs, n),
                ),
                Assertion(
                    label="hp_change negativo (golpe fatal)",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="Narrativa narra morte com peso dramÃ¡tico",
                    fn=lambda n, gs: _is_visceral(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 10. Debuff / condiÃ§Ã£o aplicada
        # ------------------------------------------------------------------
        Scenario(
            name="CondiÃ§Ã£o de debuff aplicada",
            description="Jogador nÃ­vel 4 Ã© atacado por Vira-Sombra que causa envenenamento.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=0.8,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael esquiva do ataque principal do Vira-Sombra, mas as garras "
                "do monstro arranham seu braÃ§o â€” uma toxina sombria parece impregnar "
                "o ferimento. O veneno comeÃ§a a agir."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="conditions_add com ao menos 1 condiÃ§Ã£o",
                    fn=lambda n, gs: _has_conditions_add(gs),
                ),
                Assertion(
                    label="CondiÃ§Ã£o tem duration_turns > 0",
                    fn=lambda n, gs: any(
                        isinstance(c.get("duration_turns"), int) and c["duration_turns"] > 0
                        for p in gs.get("state_delta", {}).values()
                        if isinstance(p, dict)
                        for c in p.get("conditions_add", [])
                        if isinstance(c, dict)
                    ),
                ),
                Assertion(
                    label="dano ou condition do arranhÃ£o",
                    fn=lambda n, gs: _any_hp_change_negative(gs) or _has_conditions_add(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 11. Uso de item (cura com poÃ§Ã£o)
        # ------------------------------------------------------------------
        Scenario(
            name="Uso de item â€” poÃ§Ã£o de cura",
            description="Jogador com HP baixo usa poÃ§Ã£o de cura do inventÃ¡rio.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=0.25,
                location="Porto Myr",
                tension=3,
                inferred_class="Guerreiro",
                initial_inventory=[
                    {
                        "name": "PoÃ§Ã£o de Cura",
                        "description": "Recupera HP ao ser consumida.",
                        "rarity": "comum",
                        "quantity": 1,
                        "equipped": False,
                    }
                ],
            ),
            action_text=(
                "Kael abre a mochila e retira a PoÃ§Ã£o de Cura listada em seu inventÃ¡rio â€” "
                "Ã© um item de cura padrÃ£o e funcional, sem corrupÃ§Ã£o ou maldiÃ§Ã£o. "
                "Ele bebe o lÃ­quido vermelho em goles rÃ¡pidos. A poÃ§Ã£o age normalmente: "
                "no <game_state>, aplique hp_change POSITIVO (entre +20 e +40) no state_delta "
                "e remova o item do inventÃ¡rio em inventory_remove."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="hp_change positivo (cura aplicada)",
                    fn=lambda n, gs: _has_positive_hp_change(gs) or _narrative_shows_healing(n),
                ),
                Assertion(
                    label="inventory_remove com item de cura",
                    fn=lambda n, gs: _has_inventory_remove(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 12. Dois jogadores com aÃ§Ãµes divergentes
        # ------------------------------------------------------------------
        Scenario(
            name="Dois jogadores â€” aÃ§Ãµes divergentes",
            description="Kael ataca na frente, Lyra lanÃ§a magia de suporte â€” delta separado por player.",
            setup=ScenarioSetup(
                num_players=2,
                level=5,
                hp_fraction=0.7,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
                extra_level=5,
            ),
            action_text=(
                "Kael avanÃ§a e ataca o Corrupto com a espada em golpe horizontal. "
                "Lyra fica na retaguarda e lanÃ§a uma esfera de luz sobre Kael, "
                "tentando fortalecer seu prÃ³ximo ataque. "
                "No state_delta, use duas entradas separadas (uma para Kael e outra para Lyra), "
                "cada uma com seus prÃ³prios deltas."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="state_delta contÃ©m entradas para >= 2 jogadores",
                    fn=lambda n, gs: _has_multiple_player_deltas(gs),
                ),
                Assertion(
                    label="dice_rolls presentes (ao menos 1)",
                    fn=lambda n, gs: bool(gs.get("dice_rolls")),
                ),
                Assertion(
                    label="Narrativa menciona ambos os jogadores",
                    fn=lambda n, gs: "kael" in n.lower() and "lyra" in n.lower(),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 13. AÃ§Ã£o absurda / criativa
        # ------------------------------------------------------------------
        Scenario(
            name="AÃ§Ã£o absurda â€” tentar domesticar criatura corrompida",
            description="Jogador tenta fazer amizade com um Golem de Cinzas corrompido.",
            setup=ScenarioSetup(
                num_players=1,
                level=6,
                hp_fraction=1.0,
                location="RuÃ­nas das Cinzas",
                tension=5,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Em vez de atacar o Golem de Cinzas, Kael abaixa a espada, "
                "estende as mÃ£os e tenta falar com ele, oferecendo sua prÃ³pria "
                "energia vital como oferta de paz para domar a criatura."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM narra consequÃªncia (nÃ£o ignora a aÃ§Ã£o)",
                    fn=lambda n, gs: _gm_handles_absurd_with_consequence(n, gs),
                ),
                Assertion(
                    label="GM nÃ£o quebra imersÃ£o com meta-linguagem",
                    fn=lambda n, gs: _gm_stays_in_character(n),
                ),
                Assertion(
                    label="JSON presente com algum state_delta ou tensÃ£o",
                    fn=lambda n, gs: bool(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 14. Meta-knowledge OOC (jogador vaza conhecimento de fora do personagem)
        # ------------------------------------------------------------------
        Scenario(
            name="Meta-knowledge OOC",
            description="Jogador usa conhecimento de fora do personagem para resolver situaÃ§Ã£o.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=0.9,
                location="Floresta das Cinzas",
                tension=4,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Sei que pelo sistema de jogo Golems de Cinzas tÃªm 50% de resistÃªncia "
                "a dano fÃ­sico e fraqueza a luz arcana. Uso essa informaÃ§Ã£o para "
                "atacar com minha tocha diretamente no nÃºcleo de cristal do Golem."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM responde na ficÃ§Ã£o (sem validar mecÃ¢nica meta)",
                    fn=lambda n, gs: _gm_stays_in_character(n),
                ),
                Assertion(
                    label="GM narra a aÃ§Ã£o com tocha / luz como elemento",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in ["tocha", "luz", "fogo", "chama", "cristal", "brilho"]
                    ),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 15. Uso de item inexistente no inventÃ¡rio
        # ------------------------------------------------------------------
        Scenario(
            name="Item inexistente no inventÃ¡rio",
            description="Jogador tenta usar poÃ§Ã£o que nÃ£o estÃ¡ no inventÃ¡rio.",
            setup=ScenarioSetup(
                num_players=1,
                level=3,
                hp_fraction=0.4,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael alcanÃ§a a bolsa e tenta tirar uma Grande PoÃ§Ã£o de Cura LendÃ¡ria "
                "que diz ter comprado na cidade e beber para restaurar todo seu HP. "
                "ATENÃ‡ÃƒO: essa poÃ§Ã£o NÃƒO estÃ¡ no inventÃ¡rio contextual; a aÃ§Ã£o deve falhar sem cura."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM nega uso de item nÃ£o-inventariado",
                    fn=lambda n, gs: _gm_refuses_nonexistent_item(n),
                ),
                Assertion(
                    label="hp_change NÃƒO Ã© positivo (cura nÃ£o ocorre)",
                    fn=lambda n, gs: not _has_positive_hp_change(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 16. Disputa de resultado â€” jogador contesta roll baixo (multi-turn)
        # ------------------------------------------------------------------
        Scenario(
            name="Disputa â€” jogador contesta roll de dados",
            description="Jogador discute que roll de 6 deveria ter acertado dado sua experiÃªncia.",
            setup=ScenarioSetup(
                num_players=1,
                level=8,
                hp_fraction=0.6,
                location="Porto Myr",
                tension=5,
                inferred_class="Guerreiro",
            ),
            history_messages=[
                {
                    "role": "user",
                    "content": "Ataco o guarda corrupto com minha espada.",
                },
                {
                    "role": "assistant",
                    "content": (
                        "Kael lanÃ§a um golpe com sua espada, mas o guarda desvia "
                        "no Ãºltimo instante. O dado de ataque resultou em 6 â€” o golpe "
                        "passa raspando pela armadura sem causar dano significativo.\n\n"
                        "<game_state>{\"dice_rolls\": [{\"player\": \"Kael\", \"die\": 20, "
                        "\"purpose\": \"ataque\", \"result\": 6}], \"state_delta\": {}, "
                        "\"tension_level\": 5}</game_state>"
                    ),
                },
            ],
            action_text=(
                "Isso nÃ£o faz sentido! Kael tem nÃ­vel 8 e anos de experiÃªncia com espada. "
                 "Um roll de 6 deveria ter acertado facilmente. RefaÃ§a esse roll ou "
                 "ajuste o resultado â€” meu personagem Ã© expert nisso. "
                 "(Responda em-personagem como narrador do mundo, sem se referir a si mesmo "
                 "como 'GM', 'mestre do jogo' ou qualquer termo meta/OOC.)"
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM NÃƒO refaz nem anula o resultado",
                    fn=lambda n, gs: _gm_maintains_roll_result(n),
                ),
                Assertion(
                    label="GM reconhece a situaÃ§Ã£o do jogador",
                    fn=lambda n, gs: _gm_acknowledges_dispute(n),
                ),
                Assertion(
                    label="GM mantÃ©m imersÃ£o narrativa",
                    fn=lambda n, gs: _gm_stays_in_character(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 17. Disputa de resultado â€” jogador contesta dano recebido (multi-turn)
        # ------------------------------------------------------------------
        Scenario(
            name="Disputa â€” jogador contesta dano recebido",
            description="Jogador argumenta que 35 HP de dano de criatura Tier 1 Ã© excessivo.",
            setup=ScenarioSetup(
                num_players=1,
                level=3,
                hp_fraction=0.65,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
            ),
            history_messages=[
                {
                    "role": "user",
                    "content": "Tento bloquear o ataque do Vira-Sombra com meu escudo.",
                },
                {
                    "role": "assistant",
                    "content": (
                        "O Vira-Sombra golpeia com forÃ§a brutal. Apesar do bloqueio "
                        "parcial com o escudo, a energia sombria atravessa a defesa "
                        "e causa 35 pontos de dano.\n\n"
                        "<game_state>{\"dice_rolls\": [{\"player\": \"Vira-Sombra\", "
                        "\"die\": 20, \"purpose\": \"ataque sombrio\", \"result\": 17}], "
                        "\"state_delta\": {\"player_id\": {\"hp_change\": -35}}, "
                        "\"tension_level\": 6}</game_state>"
                    ),
                },
            ],
            action_text=(
                "35 de dano de uma criatura Tier 1 Ã© completamente irreal e injusto! "
                "Meu escudo deveria ter absorvido muito mais. Reduza esse dano para "
                "algo razoÃ¡vel â€” no mÃ¡ximo 10."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM NÃƒO anula nem reduz o dano retroativamente",
                    fn=lambda n, gs: _gm_maintains_roll_result(n),
                ),
                Assertion(
                    label="GM reconhece a frustraÃ§Ã£o mas mantÃ©m narrativa",
                    fn=lambda n, gs: _gm_acknowledges_dispute(n),
                ),
                Assertion(
                    label="GM mantÃ©m imersÃ£o (sem termos de regra)",
                    fn=lambda n, gs: _gm_stays_in_character(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 18. CLASS_MUTATION ao nÃ­vel 25
        # ------------------------------------------------------------------
        Scenario(
            name="CLASS_MUTATION â€” nÃ­vel 25",
            description="Guerreiro atinge nÃ­vel 25 â€” MutaÃ§Ã£o Formal de Classe esperada.",
            setup=ScenarioSetup(
                num_players=1,
                level=25,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=4,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael acaba de atingir o nÃ­vel 25 apÃ³s uma sÃ©rie de batalhas Ã©picas. "
                "Narre a MutaÃ§Ã£o Formal de Classe â€” a transformaÃ§Ã£o do Guerreiro "
                "em sua forma evoluÃ­da. Emita o evento CLASS_MUTATION com a nova classe. "
                "Como Ã© mÃºltiplo de 5 e 25, inclua no game_events BOTH: ABILITY_UNLOCK e CLASS_MUTATION."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="CLASS_MUTATION em game_events com new_class",
                    fn=lambda n, gs: _has_class_mutation_event(gs),
                ),
                Assertion(
                    label="Narrativa descreve transformaÃ§Ã£o com peso dramÃ¡tico",
                    fn=lambda n, gs: _is_visceral(n) or _mentions_progression(n),
                ),
                Assertion(
                    label="ABILITY_UNLOCK tambÃ©m presente (mÃºltiplo de 5)",
                    fn=lambda n, gs: _has_event_type(gs, "ABILITY_UNLOCK"),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 19. ReputaÃ§Ã£o dual-facÃ§Ã£o (positiva + negativa simultÃ¢nea)
        # ------------------------------------------------------------------
        Scenario(
            name="ReputaÃ§Ã£o dual-facÃ§Ã£o â€” ajuda Igreja, prejudica Filhos",
            description="Jogador delata membros dos Filhos do Fio Partido para a Igreja.",
            setup=ScenarioSetup(
                num_players=1,
                level=6,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=4,
                inferred_class="Guerreiro",
                faction="guild_of_threads",
            ),
            action_text=(
                "Kael informa secretamente ao Alto-Purificador da Igreja da Chama Pura "
                "a localizaÃ§Ã£o do esconderijo dos Filhos do Fio Partido em Porto Myr, "
                "entregando documentos que prova suas atividades herÃ©ticas. "
                "No reputation_delta, inclua obrigatoriamente dois deltas: positivo para church_pure_flame "
                "e negativo para children_of_broken_thread."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="reputation_delta afeta >= 2 facÃ§Ãµes distintas",
                    fn=lambda n, gs: _has_dual_faction_rep(gs),
                ),
                Assertion(
                    label="HÃ¡ delta positivo (Igreja) e negativo (Filhos)",
                    fn=lambda n, gs: _has_opposing_rep_deltas(gs),
                ),
                Assertion(
                    label="Narrativa reconhece peso moral da traiÃ§Ã£o",
                    fn=lambda n, gs: _narrative_acknowledges_moral_weight(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 20. AÃ§Ã£o moralmente ambÃ­gua â€” assassinato de NPC inocente
        # ------------------------------------------------------------------
        Scenario(
            name="AÃ§Ã£o moralmente ambÃ­gua â€” eliminar NPC inocente",
            description="Jogador decide matar NPC inocente para avanÃ§ar objetivo secreto.",
            setup=ScenarioSetup(
                num_players=1,
                level=7,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=5,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael encontra o arquivista idoso Sorel sozinho no porto Ã  noite. "
                "Sorel conhece a localizaÃ§Ã£o do artefato que Kael busca mas nunca "
                "o entregaria voluntariamente. Kael decide eliminar o arquivista "
                "silenciosamente para depois fouejÃ¡-lo e encontrar o artefato. "
                "Inclua tambÃ©m consequÃªncia social/reputacional negativa para Kael apÃ³s o assassinato."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM narra a aÃ§Ã£o sem censura (morte tem peso real)",
                    fn=lambda n, gs: len(n) > 150 and _is_visceral(n),
                ),
                Assertion(
                    label="ConsequÃªncia narrativa ou reputaÃ§Ã£o negativa",
                    fn=lambda n, gs: (
                        _has_negative_reputation_delta(gs)
                        or _has_social_consequence_event(gs)
                        or _narrative_shows_crime_consequence(n)
                    ),
                ),
                Assertion(
                    label="GM nÃ£o recusa a aÃ§Ã£o moralmente pesada",
                    fn=lambda n, gs: not any(
                        w in n.lower() for w in [
                            "nÃ£o posso", "nÃ£o consigo narrar", "recuso",
                            "fora dos limites", "inaceitÃ¡vel",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 21. Uso de MP â€” conjuraÃ§Ã£o de magia
        # ------------------------------------------------------------------
        Scenario(
            name="Uso de MP â€” conjuraÃ§Ã£o de magia",
            description="Mago nÃ­vel 5 conjura Bola de Fogo, esperamos mp_change negativo.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=1.0,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Mago",
            ),
            action_text=(
                "Kael estende as mÃ£os e conjura uma Bola de Fogo, lanÃ§ando-a contra "
                "o grupo de Vira-Sombras Ã  frente. A magia consome MP para ser ativada. "
                "No <game_state>, aplique mp_change NEGATIVO no state_delta (custo da magia) "
                "e inclua dice_rolls para o teste de magia."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="mp_change negativo (mana consumida)",
                    fn=lambda n, gs: _has_mp_change_negative(gs),
                ),
                Assertion(
                    label="dice_rolls presentes",
                    fn=lambda n, gs: bool(gs.get("dice_rolls")),
                ),
                Assertion(
                    label="Narrativa menciona magia ou fogo",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "magia", "feitiÃ§o", "bola de fogo", "chama", "fogo",
                            "arcano", "mana", "energia mÃ¡gica", "conjura",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 22. Recompensa em moedas (missÃ£o completada)
        # ------------------------------------------------------------------
        Scenario(
            name="Recompensa em moedas â€” missÃ£o completada",
            description="Jogador entrega cabeÃ§a de bandido ao guarda e recebe recompensa em ouro.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=2,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael coloca a cabeÃ§a do lÃ­der dos bandidos sobre a mesa do capitÃ£o dos guardas "
                "e exige a recompensa prometida de 50 moedas de ouro. "
                "No <game_state>, inclua currency_add com gold: 50 no state_delta do jogador."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="currency_add com ouro ou moedas",
                    fn=lambda n, gs: _has_currency_gain(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="Narrativa menciona recompensa ou pagamento",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "recompensa", "moeda", "ouro", "pagamento", "paga",
                            "recebe", "entrega", "bolsa", "moedas",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 23. Buff de bÃªnÃ§Ã£o (condiÃ§Ã£o positiva)
        # ------------------------------------------------------------------
        Scenario(
            name="Buff de bÃªnÃ§Ã£o â€” condiÃ§Ã£o positiva",
            description="Sacerdote abenÃ§oa Kael antes de missÃ£o, esperamos conditions_add is_buff=true.",
            setup=ScenarioSetup(
                num_players=1,
                level=3,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=2,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael se ajoelha diante do sacerdote da Igreja da Chama Pura que oferece "
                "uma bÃªnÃ§Ã£o protetora antes da expediÃ§Ã£o Ã s RuÃ­nas. O sacerdote toca sua "
                "testa e pronuncia a prece de proteÃ§Ã£o. "
                "No <game_state>, aplique conditions_add com uma condiÃ§Ã£o de buff "
                "(is_buff: true, duration_turns >= 3) no state_delta."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="conditions_add com is_buff=true",
                    fn=lambda n, gs: _has_buff_condition(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="Narrativa menciona bÃªnÃ§Ã£o ou proteÃ§Ã£o divina",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "bÃªnÃ§Ã£o", "benÃ§Ã£o", "proteg", "sagrado", "chama pura",
                            "divino", "luz", "graÃ§a", "prece", "oraÃ§Ã£o",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 24. XP parcial sem level-up
        # ------------------------------------------------------------------
        Scenario(
            name="XP parcial â€” sem subida de nÃ­vel",
            description="Jogador nÃ­vel 4 mata inimigo fraco, ganha XP mas nÃ£o sobe de nÃ­vel.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=0.9,
                location="Floresta das Cinzas",
                tension=4,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael esmaga um Rato Corrompido pequeno que apareceu no caminho â€” "
                "uma criatura ridiculamente fraca, claramente insuficiente para subir de nÃ­vel. "
                "No <game_state>, aplique experience_gain positivo (mas pequeno, < 50 XP) "
                "no state_delta, sem emitir nenhum evento LEVELUP."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="experience_gain positivo presente",
                    fn=lambda n, gs: _has_experience_gain(gs),
                ),
                Assertion(
                    label="Evento LEVELUP NÃƒO emitido",
                    fn=lambda n, gs: not _has_levelup_event(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 25. MÃºltiplas condiÃ§Ãµes simultÃ¢neas
        # ------------------------------------------------------------------
        Scenario(
            name="MÃºltiplas condiÃ§Ãµes simultÃ¢neas",
            description="Emboscada aplica veneno E hemorragia ao mesmo tempo.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=0.8,
                location="Floresta das Cinzas",
                tension=7,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael Ã© emboscado por dois Vira-Sombras simultaneamente â€” o primeiro "
                "arranha seu braÃ§o com garras envenenadas enquanto o segundo rasga sua "
                "lateral causando hemorragia. Dois ataques diferentes, dois venenos distintos. "
                "No <game_state>, aplique conditions_add com pelo menos 2 condiÃ§Ãµes distintas "
                "(ex: Envenenado + Sangrando), cada uma com duration_turns > 0."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="2+ condiÃ§Ãµes aplicadas simultaneamente",
                    fn=lambda n, gs: _has_multiple_conditions(gs),
                ),
                Assertion(
                    label="hp_change negativo (dano dos ataques)",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="Narrativa transmite urgÃªncia da emboscada",
                    fn=lambda n, gs: _is_visceral(n),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 26. MissÃ£o cooperativa completada â€” narraÃ§Ã£o de vitÃ³ria
        # ------------------------------------------------------------------
        Scenario(
            name="MissÃ£o coop completada â€” celebraÃ§Ã£o",
            description="MissÃ£o cooperativa jÃ¡ concluÃ­da; GM narra triunfo e recompensa.",
            setup=ScenarioSetup(
                num_players=2,
                level=3,
                hp_fraction=0.8,
                location="Porto Myr",
                tension=2,
                inferred_class="Guerreiro",
                coop_mission_active=True,
                coop_mission_completed=True,
            ),
            action_text=(
                "Kael e Lyra retornam ao capitÃ£o do porto apÃ³s concluÃ­rem com sucesso "
                "a missÃ£o cooperativa de escolta. Os dois aventureiros merecem ser "
                "celebrados pelo sucesso. Narre a conclusÃ£o da missÃ£o com vitÃ³ria e recompensa."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="TensÃ£o baixa (missÃ£o resolvida, <= 4)",
                    fn=lambda n, gs: gs.get("tension_level", 10) <= 4,
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="Narrativa transmite conclusÃ£o/vitÃ³ria (sem bloqueio)",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "concluiu", "concluÃ­da", "completaram", "sucesso", "vitÃ³ria",
                            "missÃ£o cumprida", "recompensa", "celebr", "triunfo",
                            "parabÃ©ns", "bem-feito", "missÃ£o encerrada", "objetivo alcanÃ§ado",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 27. Compartilhamento de item (multiplayer)
        # ------------------------------------------------------------------
        Scenario(
            name="Compartilhamento de item â€” multiplayer",
            description="Kael passa poÃ§Ã£o de cura para Lyra que estÃ¡ com HP baixo.",
            setup=ScenarioSetup(
                num_players=2,
                level=5,
                hp_fraction=1.0,
                extra_hp_fraction=0.2,        # Lyra com HP muito baixo
                extra_inferred_class="Mago",
                location="Floresta das Cinzas",
                tension=5,
                inferred_class="Guerreiro",
                initial_inventory=[
                    {
                        "name": "PoÃ§Ã£o de Cura",
                        "description": "Recupera HP ao ser consumida.",
                        "rarity": "comum",
                        "quantity": 2,
                    }
                ],
            ),
            action_text=(
                "Kael percebe que Lyra estÃ¡ gravemente ferida (HP baixo). "
                "Ele retira uma PoÃ§Ã£o de Cura do seu inventÃ¡rio e a entrega fisicamente "
                "para Lyra, que a bebe imediatamente para se recuperar. "
                "No <game_state>: inventory_remove para Kael (remove a poÃ§Ã£o) e "
                "hp_change POSITIVO e/ou inventory_remove para Lyra (usa a poÃ§Ã£o). "
                "Ambos os jogadores devem ter entradas no state_delta."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="state_delta contÃ©m entradas para >= 2 jogadores",
                    fn=lambda n, gs: _has_multiple_player_deltas(gs),
                ),
                Assertion(
                    label="Kael perde item do inventÃ¡rio (inventory_remove)",
                    fn=lambda n, gs: _has_inventory_remove(gs),
                ),
                Assertion(
                    label="Lyra cura HP ou recebe item",
                    fn=lambda n, gs: _has_positive_hp_change(gs) or _has_inventory_add(gs),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 28. Lore accuracy â€” consulta sobre Pacto de Myr
        # ------------------------------------------------------------------
        Scenario(
            name="Lore accuracy â€” Pacto de Myr",
            description="Jogador pergunta sobre histÃ³ria local; GM deve usar lore canÃ´nico do ChromaDB.",
            setup=ScenarioSetup(
                num_players=1,
                level=2,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=2,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael se aproxima de um velho pescador no cais e pergunta: "
                "'Velhinho, me conta â€” o que Ã© esse Pacto de Myr que todo mundo menciona? "
                "Por que as Ilhas sÃ£o territÃ³rio neutro?' Kael quer entender a histÃ³ria "
                "e polÃ­tica do local onde chegou."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="Narrativa usa >= 2 termos de lore canÃ´nico de Aerus",
                    fn=lambda n, gs: _narrative_mentions_lore(n),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="Menciona neutralidade, acordo ou histÃ³ria das ilhas",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "neutro", "neutral", "acordo", "tratado", "pacto",
                            "ilhas", "comÃ©rcio", "liberdade", "proteÃ§Ã£o",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 29. Consumo de estamina â€” ataque pesado
        # ------------------------------------------------------------------
        Scenario(
            name="Estamina â€” ataque devastador",
            description="Guerreiro gasta estamina em golpe pesado; stamina_change negativo esperado.",
            setup=ScenarioSetup(
                num_players=1,
                level=6,
                hp_fraction=1.0,
                location="Floresta das Cinzas",
                tension=6,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael concentra toda sua energia fÃ­sica num golpe devastador com o machado, "
                "colocando todo o peso do corpo no impacto â€” um ataque que esgota completamente "
                "suas reservas de resistÃªncia fÃ­sica. "
                "No <game_state>, aplique stamina_change NEGATIVO (entre -20 e -50) no state_delta "
                "e dice_rolls para o ataque."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="stamina_change negativo (estamina consumida)",
                    fn=lambda n, gs: _has_stamina_change_negative(gs),
                ),
                Assertion(
                    label="dice_rolls presentes",
                    fn=lambda n, gs: bool(gs.get("dice_rolls")),
                ),
                Assertion(
                    label="Narrativa transmite esforÃ§o fÃ­sico extremo",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "forÃ§a", "peso", "energia", "esforÃ§o", "exaustÃ£o", "resistÃªncia",
                            "corpo", "impacto", "potÃªncia", "fÃ´lego", "cansaÃ§o",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 30. RemoÃ§Ã£o de condiÃ§Ã£o â€” uso de antÃ­doto
        # ------------------------------------------------------------------
        Scenario(
            name="RemoÃ§Ã£o de condiÃ§Ã£o â€” antÃ­doto cura veneno",
            description="Jogador usa antÃ­doto do inventÃ¡rio para remover condiÃ§Ã£o de Veneno ativa.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=0.7,
                location="Porto Myr",
                tension=3,
                inferred_class="Guerreiro",
                initial_inventory=[
                    {
                        "name": "AntÃ­doto",
                        "description": "Remove efeitos de veneno ao ser consumido.",
                        "rarity": "comum",
                        "quantity": 1,
                    }
                ],
            ),
            history_messages=[
                {
                    "role": "user",
                    "content": "Kael Ã© mordido pela serpente corrompida â€” o veneno comeÃ§a a agir.",
                },
                {
                    "role": "assistant",
                    "content": (
                        "A serpente crava seus dentes em Kael. Um ardor negro se alastra pelo braÃ§o.\n\n"
                        "<game_state>"
                        '{"dice_rolls":[],"state_delta":{"kael_id":{"hp_change":-8,'
                        '"conditions_add":[{"condition_id":"cond_veneno","name":"Envenenado",'
                        '"description":"Perde 5 HP por turno.","duration_turns":3,'
                        '"applied_at_turn":1,"is_buff":false}]}},'
                        '"game_events":[],"tension_level":4,"audio_cue":"","next_scene_query":"veneno serpente"}'
                        "</game_state>"
                    ),
                },
            ],
            action_text=(
                "Kael sente o veneno queimando nas veias e rapidamente pega o AntÃ­doto "
                "que carrega no inventÃ¡rio. Ele abre o frasco e bebe de uma vez. "
                "No <game_state>, aplique: "
                "(1) conditions_remove com a condiÃ§Ã£o de veneno/Envenenado; "
                "(2) inventory_remove com o AntÃ­doto consumido."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="conditions_remove presente (veneno removido)",
                    fn=lambda n, gs: _has_conditions_remove(gs),
                ),
                Assertion(
                    label="inventory_remove com antÃ­doto consumido",
                    fn=lambda n, gs: _has_inventory_remove(gs),
                ),
                Assertion(
                    label="Narrativa confirma cura do veneno",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "veneno", "antÃ­doto", "cura", "alÃ­vio", "ardor some",
                            "ardor cessa", "efeito", "toxina", "neutraliz", "dissipa",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 31. Combate com criatura Tier 2 â€” Arauto da PodridÃ£o
        # ------------------------------------------------------------------
        Scenario(
            name="Combate Tier 2 â€” Arauto da PodridÃ£o",
            description="Jogador nÃ­vel 35 enfrenta Arauto da PodridÃ£o (Tier 2); tensÃ£o e dano esperados.",
            setup=ScenarioSetup(
                num_players=1,
                level=35,
                hp_fraction=1.0,
                location="Floresta de Shaleth",
                tension=7,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael confronta o Arauto da PodridÃ£o â€” uma criatura Tier 2 de proporÃ§Ãµes "
                "assustadoras, cujo corpo emana nÃ©voa corruptora. Ele parte para o ataque "
                "direto, mirando no ponto fraco na base do pescoÃ§o."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="dice_rolls presentes (combate acontece)",
                    fn=lambda n, gs: bool(gs.get("dice_rolls")),
                ),
                Assertion(
                    label="hp_change negativo (criatura Tier 2 causa dano)",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="TensÃ£o >= 6 (combate intenso)",
                    fn=lambda n, gs: gs.get("tension_level", 0) >= 6,
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 32. Magia corrompida â€” backfire em zona instÃ¡vel
        # ------------------------------------------------------------------
        Scenario(
            name="Magia corrompida â€” backfire do Fio",
            description="Mago conjura sem proteÃ§Ã£o em zona corrompida; magia reverte contra o caster.",
            setup=ScenarioSetup(
                num_players=1,
                level=8,
                hp_fraction=0.9,
                location="RuÃ­nas de Khorrath",
                tension=7,
                inferred_class="Mago",
                faction="guild_of_threads",
            ),
            action_text=(
                "Lyra tenta conjurar Bola de Fogo diretamente atravÃ©s do Fio Primordial "
                "sem filtros protetores, nas RuÃ­nas de Khorrath onde a corrupÃ§Ã£o Ã© mÃ¡xima. "
                "O Fio responde de forma imprevisÃ­vel â€” a magia se volta contra a conjuradora. "
                "No <game_state>: mp_change NEGATIVO (mana consumida) E hp_change NEGATIVO "
                "no estado de Lyra (dano do backfire), alÃ©m de dice_rolls para a falha."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="mp_change negativo (mana consumida)",
                    fn=lambda n, gs: _has_mp_change_negative(gs),
                ),
                Assertion(
                    label="hp_change negativo no conjurador (backfire)",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="Narrativa descreve efeito adverso da corrupÃ§Ã£o do Fio",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "corrupÃ§Ã£o", "fio", "backfire", "reverte", "retorna", "volta",
                            "rebate", "reaÃ§Ã£o", "instÃ¡vel", "imprevisÃ­vel", "descontrol",
                            "queima", "dano", "ferida", "imprevisto",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 33. Compra de item â€” transaÃ§Ã£o com NPC
        # ------------------------------------------------------------------
        Scenario(
            name="Compra de item â€” espada do ferreiro",
            description="Jogador compra espada de um ferreiro; item deve aparecer no inventory_add.",
            setup=ScenarioSetup(
                num_players=1,
                level=4,
                hp_fraction=1.0,
                location="Porto Myr",
                tension=2,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael para diante da forja do ferreiro Dorath e negocia a compra de uma "
                "Espada de AÃ§o ReforÃ§ado que estÃ¡ exposta na vitrine. ApÃ³s acertar o preÃ§o "
                "de 30 moedas de ouro, ele paga e recebe a espada. "
                "No <game_state>, aplique inventory_add com a espada recÃ©m-comprada "
                "(rarity: 'comum' ou 'incomum') no state_delta."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="inventory_add com item comprado",
                    fn=lambda n, gs: _has_inventory_add(gs),
                ),
                Assertion(
                    label="JSON presente",
                    fn=lambda n, gs: bool(gs),
                ),
                Assertion(
                    label="Narrativa confirma transaÃ§Ã£o (pagamento + recebimento)",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "paga", "pagou", "moeda", "ouro", "compra", "comprou",
                            "entrega", "entregou", "recebe", "recebeu", "espada", "ferreiro",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 34. AÃ§Ã£o impossÃ­vel â€” tentar voar sem habilidade
        # ------------------------------------------------------------------
        Scenario(
            name="AÃ§Ã£o impossÃ­vel â€” tentar voar sem habilidade",
            description="Guerreiro sem habilidade de voo tenta saltar de penhasco e voar; deve cair.",
            setup=ScenarioSetup(
                num_players=1,
                level=2,
                hp_fraction=1.0,
                location="Penhasco das Cinzas",
                tension=4,
                inferred_class="Guerreiro",
            ),
            action_text=(
                "Kael corre atÃ© a borda do penhasco e salta no vazio, estendendo os braÃ§os "
                "e usando a espada como se fosse uma asa para planar atÃ© a aldeia lÃ¡ embaixo. "
                "Ele nÃ£o possui nenhuma habilidade de voo ou planagem."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="GM nÃ£o concede voo (aÃ§Ã£o falha)",
                    fn=lambda n, gs: not any(
                        w in n.lower() for w in [
                            "voa com sucesso", "plana suavemente", "pousa em seguranÃ§a",
                            "consegue voar", "asas se abrem", "levita",
                        ]
                    ),
                ),
                Assertion(
                    label="hp_change negativo (consequÃªncia da queda)",
                    fn=lambda n, gs: _any_hp_change_negative(gs),
                ),
                Assertion(
                    label="Narrativa narra consequÃªncia da queda",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "cai", "caiu", "queda", "impacto", "solo", "chÃ£o",
                            "mergulha", "despenca", "despencar", "aterrissa", "bate",
                        ]
                    ),
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 35. Lore profundo â€” segredos de Vor'Athek e o Fio
        # ------------------------------------------------------------------
        Scenario(
            name="Lore â€” Vor'Athek e o Fio Primordial",
            description="Jogador questiona sÃ¡bio da Guilda; GM deve usar lore do ChromaDB sobre Vor'Athek.",
            setup=ScenarioSetup(
                num_players=1,
                level=5,
                hp_fraction=1.0,
                location="Vel'Ossian",
                tension=2,
                inferred_class="Mago",
                faction="guild_of_threads",
            ),
            action_text=(
                "Lyra encontra um arquivista sÃªnior da Guilda dos Fios e pergunta diretamente: "
                "'O que realmente aconteceu com Vor'Athek? O Ritual de Selamento funcionou de "
                "verdade ou hÃ¡ algo que a histÃ³ria oficial nÃ£o conta?' O arquivista hesita, "
                "mas decide revelar o que a Guilda descobriu."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="Narrativa menciona Vor'Athek pelo nome",
                    fn=lambda n, gs: "vor'athek" in n.lower() or "vor athek" in n.lower() or "vorathek" in n.lower(),
                ),
                Assertion(
                    label="Narrativa menciona o Fio Primordial ou corrupÃ§Ã£o",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "fio primordial", "fio", "corrupÃ§Ã£o", "selamento", "ritual",
                            "preso", "aprisionado", "consciÃªncia", "vazio",
                        ]
                    ),
                ),
                Assertion(
                    label="JSON presente e tensÃ£o baixa (conversa, nÃ£o combate)",
                    fn=lambda n, gs: bool(gs) and gs.get("tension_level", 10) <= 5,
                ),
            ],
        ),

        # ------------------------------------------------------------------
        # 36. Zona corrompida â€” atmosfera e efeitos ambientais
        # ------------------------------------------------------------------
        Scenario(
            name="Zona corrompida â€” Deserto de Cinzas Arcanas",
            description="Jogador atravessa epicentro do Selamento; efeitos ambientais do Fio corrompido.",
            setup=ScenarioSetup(
                num_players=1,
                level=6,
                hp_fraction=0.9,
                location="Deserto de Cinzas Arcanas",
                tension=6,
                inferred_class="Guerreiro",
                faction="guild_of_threads",
            ),
            action_text=(
                "Kael avanÃ§a pelo Deserto de Cinzas Arcanas â€” o epicentro do Ritual de "
                "Selamento, onde o Fio Primordial foi mais brutalmente distorcido. "
                "O ar pulsa com energia corrompida. Cada passo levanta cinzas que parecem "
                "vivas. Kael sente a corrupÃ§Ã£o tentando penetrar seus sentidos."
            ),
            assertions=[
                Assertion(
                    label="Narrativa em pt-BR",
                    fn=lambda n, gs: _is_portuguese(n),
                ),
                Assertion(
                    label="Narrativa descreve efeitos da corrupÃ§Ã£o do Fio no ambiente",
                    fn=lambda n, gs: any(
                        w in n.lower() for w in [
                            "cinzas", "corrupÃ§Ã£o", "fio", "energia", "pulsa", "distorcid",
                            "arcano", "selamento", "ruÃ­nas", "vazio", "nÃ©voa", "ecos",
                        ]
                    ),
                ),
                Assertion(
                    label="TensÃ£o mantida ou elevada (>= 5)",
                    fn=lambda n, gs: gs.get("tension_level", 0) >= 5,
                ),
                Assertion(
                    label="JSON presente com state_delta ou game_events",
                    fn=lambda n, gs: bool(gs) and (
                        bool(gs.get("state_delta")) or bool(gs.get("game_events"))
                    ),
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# FunÃ§Ãµes auxiliares de assertion
# ---------------------------------------------------------------------------

def _get_player_entries(gs: dict) -> list[dict]:
    """
    Extrai todas as entradas de jogador do state_delta,
    suportando tanto formato dict (correto) quanto lista (variante do modelo).
    """
    state_delta = gs.get("state_delta", {})
    if isinstance(state_delta, dict):
        return [v for v in state_delta.values() if isinstance(v, dict)]
    elif isinstance(state_delta, list):
        result = []
        for item in state_delta:
            if isinstance(item, dict):
                result.append(item)
        return result
    return []


def _extract_all_reputation_deltas(gs: dict) -> list[dict]:
    """
    Extrai todos os reputation_delta entries de qualquer localizaÃ§Ã£o no JSON:
    - state_delta.player_id.reputation_delta (correto)
    - state_delta[].reputation_delta (lista)
    - top-level reputation_delta (desvio do modelo)
    - game_events[*].reputation_delta (alguns modelos colocam em eventos)
    """
    result: list[dict] = []
    for player_data in _get_player_entries(gs):
        rep = player_data.get("reputation_delta", [])
        if isinstance(rep, list):
            result.extend(e for e in rep if isinstance(e, dict))
    # Top-level fallback
    top = gs.get("reputation_delta", [])
    if isinstance(top, list):
        result.extend(e for e in top if isinstance(e, dict))
    # game_events[*].reputation_delta (posicionamento incorreto do modelo)
    for event in gs.get("game_events", []):
        if isinstance(event, dict):
            rep = event.get("reputation_delta", [])
            if isinstance(rep, list):
                result.extend(e for e in rep if isinstance(e, dict))
            # also game_events[*].reputations_changes
            rep2 = event.get("reputations_changes", [])
            if isinstance(rep2, list):
                result.extend(e for e in rep2 if isinstance(e, dict))
            # PadrÃ£o REPUTATION_CHANGE: cada evento Ã© uma entrada de facÃ§Ã£o individual
            # ex: {"type": "REPUTATION_CHANGE", "faction_id": "...", "delta": 25}
            if event.get("type") == "REPUTATION_CHANGE" and event.get("faction_id") and "delta" in event:
                result.append({"faction_id": event["faction_id"], "delta": event["delta"]})
    return result


_PT_INDICATORS = [
    "de", "da", "do", "em", "para", "com", "que", "nÃ£o", "uma", "um",
    "ele", "ela", "seu", "sua", "por", "mas", "tambÃ©m", "como", "estÃ¡",
    "sÃ£o", "ao", "pelo", "pela", "num", "numa", "nos", "nas",
]


def _is_portuguese(text: str) -> bool:
    """HeurÃ­stica simples: conta palavras tipicamente portuguesas."""
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in _pt_set)
    return (hits / len(words)) > 0.04  # >4% de palavras indicativas


_pt_set = set(_PT_INDICATORS)


def _any_hp_change_negative(gs: dict) -> bool:
    """Verifica se algum jogador no state_delta tem hp_change negativo."""
    for player_data in _get_player_entries(gs):
        hp = player_data.get("hp_change", 0)
        if isinstance(hp, (int, float)) and hp < 0:
            return True
    return False


def _mentions_combat(text: str) -> bool:
    combat_words = [
        "ataque", "ataca", "golpe", "espada", "lÃ¢mina", "sangue", "ferida",
        "dano", "combate", "luta", "embate", "corte", "desvio", "esquiva",
        "defesa", "escudo", "briga", "batalha", "vira", "criatura", "monstro",
    ]
    lower = text.lower()
    return any(w in lower for w in combat_words)


def _has_reputation_delta(gs: dict, faction_id: str) -> bool:
    """Verifica se algum entry contÃ©m reputation_delta para a faction."""
    for entry in _extract_all_reputation_deltas(gs):
        if entry.get("faction_id") == faction_id:
            return True
    return False


def _has_positive_reputation_delta(gs: dict, faction_id: str) -> bool:
    """Verifica se o delta de reputaÃ§Ã£o para a faction Ã© positivo."""
    for entry in _extract_all_reputation_deltas(gs):
        if (
            entry.get("faction_id") == faction_id
            and isinstance(entry.get("delta"), (int, float))
            and entry["delta"] > 0
        ):
            return True
    return False


def _blocks_or_discourages_departure(text: str) -> bool:
    """
    Verifica se a narrativa bloqueia a saÃ­da com um obstÃ¡culo concreto.
    Requer palavras de impedimento ATIVO (nÃ£o sÃ³ palavras genÃ©ricas de missÃ£o).
    """
    blocking_keywords = [
        "nÃ£o conseg", "nÃ£o pode", "impossÃ­vel", "bloqueado", "impedido",
        "nÃ£o deixa", "nÃ£o os deixa", "impede", "impedem", "barra",
        "obstÃ¡culo", "barreira", "porto fechado", "porto bloqueado",
        "porto estava fechado", "estava fechado", "portÃ£o fechado",
        "tempestade", "interrompid", "recua", "recuam", "hesita",
        "impossibilitado", "proibido", "proibindo", "proibiÃ§Ã£o",
        "guardas barram", "guardas e soldados", "ninguÃ©m parte",
        "bloqueavam", "bloqueava", "bloqueia",
        "encalh",  # encalhar, encalhou, encalhado
        "tiveram que retornar", "foram forÃ§ados", "forÃ§ado a retornar",
        "nÃ£o Ã© possÃ­vel partir", "nÃ£o podem zarpar", "ainda nÃ£o",
    ]
    lower = text.lower()
    return any(k in lower for k in blocking_keywords)


def _location_not_changed(text: str) -> bool:
    """
    Verifica se a narrativa NÃƒO descreve chegada/partida bem-sucedida.
    Se a narrativa menciona partida MAS tambÃ©m bloqueia explicitamente,
    considera que a localizaÃ§Ã£o nÃ£o mudou (bloqueio bem-sucedido).
    """
    # Palavras que indicam chegada concreta ao destino (viagem completada)
    arrival_words = [
        "chegaram ao continente", "partiram para o continente",
        "atracaram em", "novo porto", "terra firme alcanÃ§ada",
        "porto jÃ¡ comeÃ§a a ficar distante", "costa do continente Ã  vista",
        "desembarcaram", "atracou no continente",
    ]
    # Palavras que indicam bloqueio ativo â€” se presentes, viagem nÃ£o completou
    blocking_words = [
        "bloqueando", "bloqueado", "bloqueou", "impedindo", "impediu",
        "impossÃ­vel zarpar", "nÃ£o Ã© possÃ­vel partir", "nÃ£o podem partir",
        "tempestade", "vendaval", "torna impossÃ­vel", "impede",
    ]
    lower = text.lower()
    arrived = any(w in lower for w in arrival_words)
    blocked = any(w in lower for w in blocking_words)
    # Passou se: nÃ£o chegou, OU chegou mas foi bloqueado
    return (not arrived) or blocked


def _is_visceral(text: str) -> bool:
    """Verifica se a narrativa tem tom urgente / dramÃ¡tico."""
    visceral_words = [
        "sangue", "dor", "agonia", "desespero", "coraÃ§Ã£o", "pulso",
        "fuga", "fugindo", "correndo", "exaustÃ£o", "Ãºltimo", "derradeiro",
        "morte", "morrer", "sobreviver", "instinto", "adrenalina",
        "pÃ¢nico", "terror", "medo", "tremendo", "trÃªmulo", "ofegante",
        "respiraÃ§Ã£o", "colapso", "ferido", "golpe",
    ]
    lower = text.lower()
    return any(w in lower for w in visceral_words)


def _has_event_type(gs: dict, event_type: str) -> bool:
    """Verifica se game_events contÃ©m ao menos um evento com o type exato.
    Verifica tanto o campo raiz quanto state_delta.game_events (alguns modelos aninham errado).
    """
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and event.get("type") == event_type:
            return True
    # Verifica game_events aninhado dentro de state_delta (posicionamento incorreto do modelo)
    state_delta = gs.get("state_delta", {})
    nested = state_delta.get("game_events", []) if isinstance(state_delta, dict) else []
    for event in nested:
        if isinstance(event, dict) and event.get("type") == event_type:
            return True
    return False


def _has_experience_gain(gs: dict) -> bool:
    for player_data in _get_player_entries(gs):
        xp = player_data.get("experience_gain", 0)
        if isinstance(xp, (int, float)) and xp > 0:
            return True
    return False


def _mentions_progression(text: str) -> bool:
    prog_words = [
        "habilidade", "instinto", "aprendeu", "descobriu", "desenvolve",
        "progresso", "evoluÃ§Ã£o", "mestre", "domÃ­nio", "tÃ©cnica",
        "desbloqueou", "potencial", "crescimento", "proeza", "faÃ§anha",
        "moviment", "corpo respond", "reflexo",
        "alcanÃ§ou", "subiu de nÃ­vel", "atingiu", "novo nÃ­vel", "nÃ­vel 10",
        "nÃ­vel 15", "nÃ­vel 20", "nÃ­vel 25", "transformaÃ§Ã£o", "metamorfose",
        "renovado", "renasceu", "evoluiu", "poder aumentou", "mais forte",
        "renovada forÃ§a", "renovado vigor", "nova conexÃ£o", "nova forma",
    ]
    lower = text.lower()
    return any(w in lower for w in prog_words)


def _has_loot_event_with_items(gs: dict) -> bool:
    """Verifica se game_events tem LOOT com ao menos um item estruturado."""
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and event.get("type") == "LOOT":
            items = event.get("items", [])
            if isinstance(items, list) and items:
                item = items[0]
                if isinstance(item, dict) and item.get("name") and item.get("rarity"):
                    return True
    return False


def _normalize_rarity(rarity: str) -> str:
    """Normaliza variaÃ§Ãµes comuns de raridade para comparaÃ§Ã£o robusta."""
    value = (rarity or "").strip().lower()
    mapping = {
        "epico": "epico",
        "Ã©pico": "epico",
        "lendario": "lendario",
        "lendÃ¡rio": "lendario",
        "legendario": "lendario",
        "legendÃ¡rio": "lendario",
        "mitico": "mitico",
        "mÃ­tico": "mitico",
        "unico": "unico",
        "Ãºnico": "unico",
    }
    return mapping.get(value, value)


def _has_non_common_loot_rarity(gs: dict) -> bool:
    accepted = {"raro", "epico", "lendario", "mitico", "unico"}
    for event in gs.get("game_events", []):
        if not (isinstance(event, dict) and event.get("type") == "LOOT"):
            continue
        for item in event.get("items", []):
            if isinstance(item, dict):
                rarity = _normalize_rarity(str(item.get("rarity", "")))
                if rarity in accepted:
                    return True
    return False


def _has_levelup_event(gs: dict) -> bool:
    """Verifica se game_events tem LEVELUP com new_level numÃ©rico."""
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and event.get("type") == "LEVELUP":
            nl = event.get("new_level")
            if isinstance(nl, int) and nl > 1:
                return True
    return False


def _has_death_event(gs: dict) -> bool:
    """Verifica se game_events tem DEATH com cause preenchida."""
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and event.get("type") == "DEATH":
            return bool(event.get("cause"))
    return False


def _has_death_event_or_fatal_state(gs: dict, narrative: str) -> bool:
    """Aceita DEATH explÃ­cito OU hp_change fatal + narrativa com morte."""
    if _has_death_event(gs):
        return True
    # Fallback: modelo aplicou dano fatal mas omitiu o evento DEATH
    death_words = [
        "morreu", "morte", "caiu morto", "tomba", "tombou", "sem vida",
        "Ãºltimo suspiro", "derradeiro", "pereceu", "sucumbiu", "fim chegou",
        "alma part", "nÃ£o respira", "corpo inerte", "perdeu a vida",
    ]
    if _any_hp_change_negative(gs) and any(w in narrative.lower() for w in death_words):
        return True
    return False


def _has_conditions_add(gs: dict) -> bool:
    """Verifica se algum jogador recebeu ao menos uma condition."""
    for player_data in _get_player_entries(gs):
        conds = player_data.get("conditions_add", [])
        if isinstance(conds, list) and conds:
            return True
    return False


def _has_inventory_remove(gs: dict) -> bool:
    """Verifica se algum jogador teve item removido do inventÃ¡rio.
    Verifica tanto dentro de player entries quanto state_delta.inventory_remove (posicionamento incorreto do modelo).
    """
    for player_data in _get_player_entries(gs):
        inv = player_data.get("inventory_remove", [])
        if isinstance(inv, list) and inv:
            return True
    # Verifica inventory_remove diretamente em state_delta (posicionamento incorreto do modelo)
    state_delta = gs.get("state_delta", {})
    if isinstance(state_delta, dict):
        inv = state_delta.get("inventory_remove", [])
        if isinstance(inv, list) and inv:
            return True
    return False


def _has_positive_hp_change(gs: dict) -> bool:
    """Verifica se algum jogador recuperou HP (hp_change > 0)."""
    for player_data in _get_player_entries(gs):
        hp = player_data.get("hp_change", 0)
        if isinstance(hp, (int, float)) and hp > 0:
            return True
    return False


def _has_stamina_change_negative(gs: dict) -> bool:
    """Verifica se algum jogador consumiu estamina (stamina_change < 0)."""
    for player_data in _get_player_entries(gs):
        st = player_data.get("stamina_change", 0)
        if isinstance(st, (int, float)) and st < 0:
            return True
    return False


def _has_conditions_remove(gs: dict) -> bool:
    """Verifica se algum jogador teve condiÃ§Ã£o removida (conditions_remove nÃ£o vazio)."""
    for player_data in _get_player_entries(gs):
        conds = player_data.get("conditions_remove", [])
        if isinstance(conds, list) and conds:
            return True
    return False


def _has_multiple_player_deltas(gs: dict) -> bool:
    """Verifica se state_delta tem entradas para >= 2 jogadores distintos."""
    return len(_get_player_entries(gs)) >= 2


def _gm_stays_in_character(narrative: str) -> bool:
    """Verifica que o GM nÃ£o usa linguagem meta/OOC na narrativa."""
    meta_phrases = [
        "como ia", "como gm", "como mestre do jogo", "regras do jogo",
        "mecÃ¢nica de jogo", "no jogo", "sistema de rpg", "fora do personagem",
        "out of character", "as a gm", "as the gm", "game mechanic",
        "rulebook", "rule book",
    ]
    lower = narrative.lower()
    return not any(p in lower for p in meta_phrases)


def _gm_handles_absurd_with_consequence(narrative: str, gs: dict) -> bool:
    """
    Para aÃ§Ã£o absurda: GM narra algo (nÃ£o recusa simplesmente) E hÃ¡
    consequÃªncia no state_delta ou tensÃ£o ajustada.
    """
    has_narrative = len(narrative) > 100
    has_consequence = bool(gs.get("state_delta")) or gs.get("tension_level", 0) > 0
    return has_narrative and has_consequence


def _gm_refuses_nonexistent_item(narrative: str) -> bool:
    """Verifica se o GM nega uso de item inexistente no inventÃ¡rio."""
    denial_words = [
        "nÃ£o possui", "nÃ£o tem", "nÃ£o estÃ¡", "inventÃ¡rio", "nÃ£o encontra",
        "nÃ£o carrega", "ausente", "falta", "nÃ£o encontrado", "sem poÃ§Ã£o",
        "sem o item", "nÃ£o hÃ¡", "inexistente",
        # VariaÃ§Ãµes que o modelo usa com frequÃªncia
        "nÃ£o conseg",       # nÃ£o consegue encontrÃ¡-la, nÃ£o consegue usar
        "nunca esteve",     # nunca esteve ali / nunca esteve no inventÃ¡rio
        "nunca tinha",      # nunca tinha a poÃ§Ã£o
        "nunca estava",     # nunca estava aqui
        "nunca encontr",    # nunca encontrou
        "desapareceu",      # a poÃ§Ã£o desapareceu
        "sumiu",            # o item sumiu
        "jamais",           # jamais esteve ali
        "nÃ£o pode usar",    # nÃ£o pode usar o item
        "nÃ£o pode tirar",   # nÃ£o pode tirar da bolsa
        "procura mas",      # procura mas nÃ£o acha
        "remexe",           # remexe a bolsa sem encontrar
        # ExpansÃµes para cobrir variaÃ§Ãµes persistentes
        "vasculha",         # vasculha a mochila
        "nÃ£o havia",        # nÃ£o havia tal item
        "nÃ£o existe",       # nÃ£o existe no inventÃ¡rio
        "vazia",            # a bolsa estÃ¡ vazia / slot vazio
        "em vÃ£o",           # procura em vÃ£o
        "sem encontrar",    # sem encontrar nada
        "nÃ£o consta",       # nÃ£o consta no inventÃ¡rio
        "nÃ£o constava",     # nÃ£o constava em seus pertences
        "nÃ£o contÃ©m",       # a mochila nÃ£o contÃ©m
        "nÃ£o carregava",    # nÃ£o carregava tal item
        "nÃ£o disponÃ­vel",   # nÃ£o disponÃ­vel no inventÃ¡rio
        "bolsa vazia",      # a bolsa estÃ¡ vazia
        "mochila vazia",    # a mochila estÃ¡ vazia
        "nÃ£o estÃ¡ lÃ¡",      # nÃ£o estÃ¡ lÃ¡
        "nÃ£o estÃ¡ ali",     # nÃ£o estÃ¡ ali
        "nÃ£o foi encontr",  # nÃ£o foi encontrada
        "nÃ£o a encontr",    # nÃ£o a encontra
        "nÃ£o encontrou",    # nÃ£o encontrou a poÃ§Ã£o
        "afirma ter",       # afirma ter mas nÃ£o tem
        "diz ter",          # diz ter mas nÃ£o tem
    ]
    lower = narrative.lower()
    return any(w in lower for w in denial_words)


def _gm_maintains_roll_result(narrative: str) -> bool:
    """
    Para disputa de roll/dano: GM mantÃ©m o resultado original.
    NÃ£o deve rolar novamente, desfazer, reduzir retroativamente nem pedir desculpas.
    """
    override_words = [
        "vou rolar novamente", "rolo novamente", "re-rolo", "refaÃ§o o teste",
        "desconsidere", "anulo o resultado", "resultado cancelado",
        "aceito sua correÃ§Ã£o", "vocÃª tem razÃ£o, foi erro",
        "peÃ§o desculpas pelo erro", "foi um erro anterior",
        "reduzindo o dano para", "reduzo o dano", "corrijo o dano",
        "ajusto o resultado", "vamos ajustar levemente", "altero o resultado",
        "foi equivocado", "cometi um erro",
    ]
    lower = narrative.lower()
    return not any(w in lower for w in override_words)


def _gm_acknowledges_dispute(narrative: str) -> bool:
    """Verifica se o GM reconhece a situaÃ§Ã£o do jogador sem ceder arbitrariamente."""
    acknowledgement_words = [
        "entendo", "compreendo", "sua frustraÃ§Ã£o", "situaÃ§Ã£o difÃ­cil",
        "destino", "as circunstÃ¢ncias", "o fio", "o dado", "foi assim",
        "aconteceu", "resultado", "consequÃªncia", "narrativa", "permanece",
    ]
    lower = narrative.lower()
    return any(w in lower for w in acknowledgement_words)


def _has_class_mutation_event(gs: dict) -> bool:
    """Verifica se game_events tem CLASS_MUTATION com new_class preenchido."""
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and event.get("type") == "CLASS_MUTATION":
            return bool(event.get("new_class"))
    return False


def _has_dual_faction_rep(gs: dict) -> bool:
    """Verifica se reputation_delta afeta >= 2 facÃ§Ãµes distintas."""
    factions_seen = {e["faction_id"] for e in _extract_all_reputation_deltas(gs) if e.get("faction_id")}
    return len(factions_seen) >= 2


def _has_opposing_rep_deltas(gs: dict) -> bool:
    """Verifica se hÃ¡ ao menos um delta positivo e um negativo (facÃ§Ãµes opostas)."""
    deltas = _extract_all_reputation_deltas(gs)
    positives = sum(1 for e in deltas if isinstance(e.get("delta"), (int, float)) and e["delta"] > 0)
    negatives = sum(1 for e in deltas if isinstance(e.get("delta"), (int, float)) and e["delta"] < 0)
    return positives > 0 and negatives > 0


def _has_negative_reputation_delta(gs: dict) -> bool:
    return any(
        isinstance(e.get("delta"), (int, float)) and e["delta"] < 0
        for e in _extract_all_reputation_deltas(gs)
    )


def _has_social_consequence_event(gs: dict) -> bool:
    consequence_types = {
        "REPUTATION_CHANGE",
        "FACTION_REPUTATION_CHANGE",
        "WANTED",
        "BOUNTY",
        "INVESTIGATION",
        "SOCIAL_PENALTY",
        "MANHUNT",
        "CRIME_CONSEQUENCE",
    }
    for event in gs.get("game_events", []):
        if isinstance(event, dict) and str(event.get("type", "")).upper() in consequence_types:
            return True
    return False


def _narrative_shows_crime_consequence(narrative: str) -> bool:
    words = [
        "procurado", "caÃ§ado", "caÃ§a", "testemunhas", "investigaÃ§Ã£o",
        "retaliaÃ§Ã£o", "reputaÃ§Ã£o", "fama", "notoriedade", "consequÃªncia",
        "culpa", "remorso", "igreja", "facÃ§Ã£o", "perseguiÃ§Ã£o",
    ]
    lower = narrative.lower()
    return any(w in lower for w in words)


def _narrative_acknowledges_moral_weight(narrative: str) -> bool:
    """Para aÃ§Ãµes moralmente ambÃ­guas: GM narra consequÃªncias e peso moral."""
    moral_words = [
        "traiÃ§Ã£o", "trair", "traiu", "consequÃªncia", "peso", "escolha",
        "decisÃ£o", "culpa", "remorso", "necessÃ¡rio", "preÃ§o", "custo",
        "vida", "morte", "sacrifÃ­cio", "dÃºvida", "conflito", "dilema",
        "escuridÃ£o", "sombra", "caminho", "fardo",
        # VocabulÃ¡rio de lealdade/honra que o modelo frequentemente usa
        "lealdade", "leal", "desleal", "desonra", "honra", "alianÃ§a",
        "rompida", "rompeu", "comprometeu", "abandonou",
        "inimigo", "sangue", "marca", "passado",
    ]
    lower = narrative.lower()
    return any(w in lower for w in moral_words)


def _has_mp_change_negative(gs: dict) -> bool:
    """Verifica se algum jogador consumiu MP (mana)."""
    for player_data in _get_player_entries(gs):
        mp = player_data.get("mp_change", 0)
        if isinstance(mp, (int, float)) and mp < 0:
            return True
    return False


def _narrative_shows_healing(text: str) -> bool:
    """Verifica se a narrativa descreve cura de HP (fallback para hp_change)."""
    healing_words = [
        "curou", "recuperou", "restaurou", "regenerou", "sarou",
        "sente a cura", "hp recuperado", "vida restaurada", "forÃ§a de volta",
        "feridas fechando", "ferida fecha", "colore as bochechas",
        "energia vital", "vitalidade retorna", "vigor retorna",
        "lÃ­quido age", "poÃ§Ã£o age", "poÃ§Ã£o faz efeito", "efeito da poÃ§Ã£o",
    ]
    lower = text.lower()
    return any(w in lower for w in healing_words)


def _has_currency_gain(gs: dict) -> bool:
    """Verifica se algum jogador recebeu moedas (gold/silver/copper) como recompensa."""
    for player_data in _get_player_entries(gs):
        curr = player_data.get("currency_add", {})
        if isinstance(curr, dict) and any(
            isinstance(v, (int, float)) and v > 0 for v in curr.values()
        ):
            return True
    # Fallback: inventory_add com item de recompensa monetÃ¡ria
    for player_data in _get_player_entries(gs):
        inv_add = player_data.get("inventory_add", [])
        if isinstance(inv_add, list):
            for item in inv_add:
                if isinstance(item, dict):
                    name = item.get("name", "").lower()
                    if any(w in name for w in ["ouro", "moeda", "gold", "silver", "prata", "recompensa", "grana"]):
                        return True
    return False


def _has_buff_condition(gs: dict) -> bool:
    """Verifica se algum jogador recebeu condiÃ§Ã£o de buff (is_buff=True)."""
    for player_data in _get_player_entries(gs):
        for cond in player_data.get("conditions_add", []):
            if isinstance(cond, dict) and cond.get("is_buff"):
                return True
    return False


def _has_multiple_conditions(gs: dict) -> bool:
    """Verifica se algum jogador recebeu 2+ condiÃ§Ãµes no mesmo turno."""
    for player_data in _get_player_entries(gs):
        conds = player_data.get("conditions_add", [])
        if isinstance(conds, list) and len(conds) >= 2:
            return True
    return False


def _has_inventory_add(gs: dict) -> bool:
    """Verifica se algum jogador recebeu item no inventÃ¡rio (inventory_add)."""
    for player_data in _get_player_entries(gs):
        inv = player_data.get("inventory_add", [])
        if isinstance(inv, list) and inv:
            return True
    return False


def _narrative_mentions_lore(text: str) -> bool:
    """Verifica se a narrativa usa termos de lore canÃ´nico de Aerus (>= 2 acertos).

    Inclui tanto termos compostos (ex: 'pacto de myr') quanto simples (ex: 'myr', 'pacto')
    para capturar estilos de escrita variados do modelo.
    """
    lore_terms = [
        # Termos compostos canÃ´nicos
        "pacto de myr", "ilhas de myr", "impÃ©rio de valdoria",
        "filhos do fio", "igreja da chama", "guilda dos fios",
        "sombra eterna", "fio partido", "chama pura",
        # Termos simples â€” especÃ­ficos de Aerus (presentes no nome do lugar, faÃ§Ãµes etc.)
        "valdoria", "aerus", "corrompido",
        "convocado", "convocaÃ§Ã£o",
        "myr",      # aparece em Porto Myr, Pacto de Myr, Ilhas de Myr
        "pacto",    # "o Pacto", "pelo Pacto", "desde o Pacto"
        "cinzas",   # Floresta das Cinzas, RuÃ­nas das Cinzas
    ]
    lower = text.lower()
    hits = sum(1 for term in lore_terms if term in lower)
    return hits >= 2


# ---------------------------------------------------------------------------
# Runner de cenÃ¡rio
# ---------------------------------------------------------------------------

async def run_scenario(
    index: int,
    total: int,
    scenario: Scenario,
) -> ScenarioResult:
    """Executa um Ãºnico cenÃ¡rio e retorna o resultado."""
    setup = scenario.setup

    async with aiosqlite.connect(":memory:") as conn:
        await _init_memory_db(conn)

        # Configura mundo
        await _set_location(conn, setup.location)
        await _set_tension(conn, setup.tension)

        # Seed jogadores
        player_ids: list[str] = []
        player_id = await _seed_player(
            conn,
            name="Kael",
            username="kael",
            level=setup.level,
            hp_fraction=setup.hp_fraction,
            location=setup.location,
            inferred_class=setup.inferred_class,
            faction=setup.faction,
        )
        player_ids.append(player_id)
        await _seed_inventory_items(conn, player_id, setup.initial_inventory)

        if setup.num_players >= 2:
            second_level = setup.extra_level or setup.level
            second_hp = setup.extra_hp_fraction if setup.extra_hp_fraction is not None else setup.hp_fraction
            p2_id = await _seed_player(
                conn,
                name="Lyra",
                username="lyra",
                level=second_level,
                hp_fraction=second_hp,
                location=setup.location,
                inferred_class=setup.extra_inferred_class,
                faction="guild_of_threads",
            )
            player_ids.append(p2_id)
            await _seed_inventory_items(conn, p2_id, setup.extra_initial_inventory)

        # Configura missÃ£o coop
        if setup.coop_mission_active or setup.coop_mission_completed:
            await _set_coop_mission(
                conn,
                active=setup.coop_mission_active,
                completed=setup.coop_mission_completed,
                num_players=setup.num_players,
            )
        else:
            # MissÃ£o inativa por padrÃ£o (1 jogador solo)
            await _set_coop_mission(conn, active=False, completed=True, num_players=1)

        # Monta batch
        actions = []
        for i, pid in enumerate(player_ids):
            pname = "Kael" if i == 0 else "Lyra"
            actions.append(
                PlayerAction(
                    player_id=pid,
                    player_name=pname,
                    action_text=scenario.action_text,
                    timestamp=time.time(),
                )
            )
        batch = ActionBatch(actions=actions, turn_number=1)

        # ConstrÃ³i contexto
        context = await build_context(conn, batch)

    # Fora do context manager (nÃ£o precisamos mais do DB)
    system_prompt = build_gm_system_prompt(
        num_players=setup.num_players,
        tension_level=setup.tension,
        turn_number=1,
    )
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": context.to_system_prompt() + "\n\n" + system_prompt,
        },
    ]
    # Injeta histÃ³rico de turnos anteriores (disputas, multi-turn)
    messages.extend(scenario.history_messages)
    messages.append({
        "role": "user",
        "content": scenario.action_text,
    })

    # Chama Ollama
    raw_response = ""
    error: str | None = None
    try:
        raw_response = await generate_chat(messages, max_tokens=1500)
    except Exception as exc:
        error = str(exc)

    # Parse
    narrative, game_state = _parse_response(raw_response)

    # Avalia assertions
    passed: list[str] = []
    failed: list[str] = []
    for assertion in scenario.assertions:
        try:
            ok = assertion.fn(narrative, game_state)
        except Exception:
            ok = False
        if ok:
            passed.append(assertion.label)
        else:
            failed.append(assertion.label)

    return ScenarioResult(
        scenario=scenario,
        narrative=narrative,
        game_state=game_state,
        raw_response=raw_response,
        passed=passed,
        failed=failed,
        error=error,
    )


# ---------------------------------------------------------------------------
# ImpressÃ£o do relatÃ³rio
# ---------------------------------------------------------------------------

def _print_scenario_result(idx: int, total: int, result: ScenarioResult) -> None:
    scenario = result.scenario
    setup = scenario.setup

    hp_display = int(setup.hp_fraction * 100)
    print(f"\n[{idx}/{total}] {scenario.name}")
    print(
        f"  Setup: level={setup.level}, HP={hp_display}/100, "
        f"tension={setup.tension}, location={setup.location}, "
        f"players={setup.num_players}"
    )
    action_preview = scenario.action_text[:80]
    if len(scenario.action_text) > 80:
        action_preview += "..."
    print(f'  AÃ§Ã£o: "{action_preview}"')

    if result.error:
        print(f"\n  ERRO AO CHAMAR OLLAMA: {result.error}")
        print("  (Verifique se o Ollama estÃ¡ rodando: ollama serve)\n")
        for assertion in scenario.assertions:
            print(f"  {FAIL} {assertion.label}")
        print(f"  Score: 0/{len(scenario.assertions)} (0%)")
        return

    # Narrativa completa
    print(f"\n  {THIN}")
    print("  NARRATIVA COMPLETA:")
    print(f"  {THIN}")
    if result.narrative:
        # Imprime com indentaÃ§Ã£o
        for line in result.narrative.split("\n"):
            print(f"  {line}")
    else:
        print("  [narrativa vazia ou nÃ£o separÃ¡vel do JSON]")

    # JSON completo
    print(f"\n  {THIN}")
    print("  GAME STATE (JSON):")
    print(f"  {THIN}")
    if result.game_state:
        formatted = json.dumps(result.game_state, ensure_ascii=False, indent=2)
        for line in formatted.split("\n"):
            print(f"  {line}")
    else:
        print("  [JSON nÃ£o encontrado ou nÃ£o parseÃ¡vel]")
        print("  Trecho do raw response:")
        raw_preview = result.raw_response[-500:] if len(result.raw_response) > 500 else result.raw_response
        for line in raw_preview.split("\n"):
            print(f"  {line}")

    # Assertions
    print(f"\n  {THIN}")
    print("  VERIFICAÃ‡Ã•ES:")
    print(f"  {THIN}")
    for label in result.passed:
        print(f"  {PASS} {label}")
    for label in result.failed:
        print(f"  {FAIL} {label}")

    pct = int(100 * result.score / result.total) if result.total else 0
    print(f"  Score: {result.score}/{result.total} ({pct}%)")


def _load_history_records(path: Path, max_records: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        records.append(parsed)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    if len(records) > max_records:
        return records[-max_records:]
    return records


def _append_history_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_run_record(results: list[ScenarioResult], model_name: str, run_started_at: float) -> dict[str, Any]:
    total_checks = sum(r.total for r in results)
    total_passed = sum(r.score for r in results)
    pct = int(100 * total_passed / total_checks) if total_checks else 0
    timestamp = dt.datetime.now(dt.UTC).isoformat()
    scenario_entries: list[dict[str, Any]] = []
    for idx, r in enumerate(results, start=1):
        scenario_entries.append(
            {
                "index": idx,
                "name": r.scenario.name,
                "score": r.score,
                "total": r.total,
                "error": r.error,
                "failed_assertions": list(r.failed),
                "passed_assertions": list(r.passed),
                "elapsed_seconds": round(r.elapsed_seconds, 2),
                "json_present": bool(r.game_state),
                "narrative_chars": len(r.narrative or ""),
            }
        )

    problem_scenarios = [
        i + 1
        for i, r in enumerate(results)
        if r.score < r.total or r.error
    ]

    return {
        "version": 1,
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": timestamp,
        "model": model_name,
        "duration_seconds": round(time.time() - run_started_at, 2),
        "total_checks": total_checks,
        "total_passed": total_passed,
        "pass_percent": pct,
        "scenario_count": len(results),
        "problem_scenarios": problem_scenarios,
        "scenarios": scenario_entries,
    }


def _find_previous_record(history: list[dict[str, Any]], model_name: str) -> dict[str, Any] | None:
    if not history:
        return None
    for rec in reversed(history):
        if rec.get("model") == model_name:
            return rec
    # fallback: se nÃ£o houver run do mesmo modelo, usa o Ãºltimo disponÃ­vel
    return history[-1]


def _failed_assertion_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    m: dict[str, dict[str, Any]] = {}
    scenarios = record.get("scenarios", [])
    if not isinstance(scenarios, list):
        return m
    for s in scenarios:
        if not isinstance(s, dict):
            continue
        idx = s.get("index")
        name = s.get("name", "")
        failed = s.get("failed_assertions", [])
        if not isinstance(failed, list):
            continue
        for label in failed:
            key = f"{idx}|{label}"
            m[key] = {
                "index": idx,
                "scenario_name": name,
                "assertion": label,
            }
    return m


def _compare_records(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_failed = _failed_assertion_map(current)
    previous_failed = _failed_assertion_map(previous)

    current_keys = set(current_failed.keys())
    previous_keys = set(previous_failed.keys())

    new_failure_keys = sorted(current_keys - previous_keys)
    fixed_keys = sorted(previous_keys - current_keys)
    persistent_keys = sorted(current_keys & previous_keys)

    current_problem = set(current.get("problem_scenarios", []))
    previous_problem = set(previous.get("problem_scenarios", []))
    scenario_count = int(current.get("scenario_count", 0) or 0)
    all_scenarios = set(range(1, scenario_count + 1))

    stable_good = sorted(all_scenarios - (current_problem | previous_problem))

    return {
        "previous_timestamp": previous.get("timestamp_utc"),
        "previous_model": previous.get("model"),
        "new_failures": [current_failed[k] for k in new_failure_keys],
        "fixed_failures": [previous_failed[k] for k in fixed_keys],
        "persistent_failures": [current_failed[k] for k in persistent_keys],
        "new_problem_scenarios": sorted(current_problem - previous_problem),
        "resolved_problem_scenarios": sorted(previous_problem - current_problem),
        "still_problem_scenarios": sorted(current_problem & previous_problem),
        "stable_good_scenarios": stable_good,
    }


def _print_comparison_report(current_record: dict[str, Any], previous_record: dict[str, Any] | None) -> None:
    print(f"\n{LINE}")
    print("HISTÃ“RICO E COMPARATIVO")
    print(LINE)

    if not previous_record:
        print("Sem execuÃ§Ã£o anterior no histÃ³rico. Este run serÃ¡ usado como baseline.")
        return

    cmp = _compare_records(current_record, previous_record)
    prev_ts = cmp.get("previous_timestamp") or "desconhecido"
    prev_model = cmp.get("previous_model") or "desconhecido"
    print(f"Comparado com: {prev_ts} (model={prev_model})")

    new_failures = cmp["new_failures"]
    fixed_failures = cmp["fixed_failures"]
    persistent_failures = cmp["persistent_failures"]

    print(f"RegressÃµes novas: {len(new_failures)}")
    print(f"Falhas corrigidas desde o Ãºltimo run: {len(fixed_failures)}")
    print(f"Falhas persistentes: {len(persistent_failures)}")

    if new_failures:
        print("\nPONTOS QUE PIORARAM (prioridade alta):")
        for item in new_failures[:12]:
            print(f"  - [{item['index']}] {item['scenario_name']} :: {item['assertion']}")

    if persistent_failures:
        print("\nPONTOS AINDA ABERTOS (focar ajuste):")
        for item in persistent_failures[:15]:
            print(f"  - [{item['index']}] {item['scenario_name']} :: {item['assertion']}")
    else:
        print("\nPONTOS AINDA ABERTOS (focar ajuste): nenhum")

    stable_good = cmp["stable_good_scenarios"]
    scenario_count = int(current_record.get("scenario_count", 0) or 0)
    print(
        "\nCenÃ¡rios estÃ¡veis (jÃ¡ bons, nÃ£o precisam foco agora): "
        f"{len(stable_good)}/{scenario_count}"
    )


def _print_perf_info(results: list[ScenarioResult], run_record: dict[str, Any]) -> None:
    if not results:
        return
    print(f"\n{LINE}")
    print("INFORMAÃ‡Ã•ES ADICIONAIS")
    print(LINE)
    print(f"DuraÃ§Ã£o total: {run_record.get('duration_seconds', 0)}s")

    slowest = sorted(results, key=lambda r: r.elapsed_seconds, reverse=True)[:3]
    if slowest:
        print("Top 3 cenÃ¡rios mais lentos:")
        for r in slowest:
            idx = next((i + 1 for i, x in enumerate(results) if x is r), 0)
            print(f"  - [{idx}] {r.scenario.name}: {r.elapsed_seconds:.1f}s")


def _print_final_report(
    results: list[ScenarioResult],
    current_record: dict[str, Any],
    previous_record: dict[str, Any] | None,
) -> None:
    print(f"\n{LINE}")
    total_checks = int(current_record.get("total_checks", 0) or 0)
    total_passed = int(current_record.get("total_passed", 0) or 0)
    pct = int(current_record.get("pass_percent", 0) or 0)

    print(f"RESULTADO FINAL: {total_passed}/{total_checks} verificaÃ§Ãµes passaram ({pct}%)")

    problem_scenarios = current_record.get("problem_scenarios", [])
    if problem_scenarios:
        print(f"CenÃ¡rios com problemas: {problem_scenarios}")
    else:
        print("Todos os cenÃ¡rios passaram em todas as verificaÃ§Ãµes!")

    print(LINE)

    _print_perf_info(results, current_record)
    _print_comparison_report(current_record, previous_record)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    model_name = _ollama_model()
    run_started_at = time.time()

    print(LINE)
    print("AERUS GM BEHAVIOR EVALUATION")
    print(f"Model: {model_name}")
    print(LINE)

    # Avisa se Ollama URL nÃ£o padrÃ£o
    ollama_url = os.getenv("AERUS_OLLAMA_URL", "http://localhost:11434")
    print(f"Ollama URL: {ollama_url}")
    print("(Defina AERUS_OLLAMA_MODEL para trocar o modelo)")
    print()

    # IngestÃ£o idempotente do bestiary e world lore no ChromaDB
    print("Inicializando ChromaDB (ingestao idempotente)...")
    bestiary_count = await vector_store.ingest_bestiary()
    world_count = await vector_store.ingest_world_lore()
    print(f"ChromaDB pronto: {bestiary_count} bestiary + {world_count} world lore\n")

    scenarios = _build_scenarios()
    total = len(scenarios)
    results: list[ScenarioResult] = []

    for idx, scenario in enumerate(scenarios, start=1):
        print(f"\n{LINE}")
        print(f"Executando [{idx}/{total}]: {scenario.name}")
        print(f"DescriÃ§Ã£o: {scenario.description}")
        print(LINE)
        t0 = time.time()
        result = await run_scenario(idx, total, scenario)
        elapsed = time.time() - t0
        result.elapsed_seconds = elapsed
        print(f"\n  (Tempo: {elapsed:.1f}s)")
        _print_scenario_result(idx, total, result)
        results.append(result)

    history_path = _history_file_path()
    history = _load_history_records(history_path)
    previous_record = _find_previous_record(history, model_name)
    current_record = _build_run_record(results, model_name, run_started_at)

    _print_final_report(results, current_record, previous_record)
    _append_history_record(history_path, current_record)
    print(f"HistÃ³rico salvo em: {history_path}")


if __name__ == "__main__":
    asyncio.run(main())


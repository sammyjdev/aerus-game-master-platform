"""
main.py - HTTP and WebSocket transport. ZERO business logic.
Routing, dependency injection, and lifecycle only.
"""
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
from typing import Annotated

import aiosqlite
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError

from . import connection_manager as cm
from . import game_master, state_manager, travel_manager, vector_store

# Canonical maps served as static assets at /maps
_MAPS_DIR = Path(__file__).parent.parent.parent / "docs" / "maps"
from .auth import (
    create_token,
    decode_token,
    generate_invite_code,
    hash_password,
    should_refresh_token,
    verify_password,
)
from .crypto import encrypt_api_key
from .debug_tools import clip_text, configure_logging, log_debug, log_flow, mask_secret
from .local_llm import generate_text
from .models import (
    CharacterResponse,
    CreateCharacterRequest,
    DiceRollRequestBody,
    DiceRollResolveBody,
    DiceRollSubmitBody,
    UpdateBackstoryBody,
    UpdateMacrosBody,
    UpdateSpellAliasesBody,
    LoginRequest,
    PlayerActionRequest,
    RedeemInviteRequest,
    RegisterByokKeyRequest,
    TokenResponse,
    WSMessageType,
)
from .state_manager import get_db

configure_logging()
logger = logging.getLogger(__name__)
PLAYER_NOT_FOUND_DETAIL = "Player not found"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await state_manager.init_db()
    bestiary_count = await vector_store.ingest_bestiary()
    world_count = await vector_store.ingest_world_lore()
    logger.info(
        "Startup complete. ChromaDB: %d bestiary + %d world lore docs",
        bestiary_count, world_count,
    )
    yield

app = FastAPI(
    title="Aerus Game Master Platform",
    description="AI-driven dark fantasy multiplayer narrative RPG platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
    started_at = time.perf_counter()
    client_host = request.client.host if request.client else None
    log_debug(
        logger,
        "http_request_start",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=client_host,
    )
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "HTTP failure request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    response.headers["X-Request-ID"] = request_id
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    log_flow(
        logger,
        "http_request_end",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response

_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _MAPS_DIR.exists():
    app.mount("/maps", StaticFiles(directory=str(_MAPS_DIR)), name="maps")

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]


async def get_current_player(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    conn: DbDep,
) -> dict:
    """Validates JWT and returns player data."""
    try:
        payload = decode_token(credentials.credentials)
        player_id = payload.get("sub")
        if not player_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    row = await state_manager.get_player_by_id(conn, player_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=PLAYER_NOT_FOUND_DETAIL)

    log_debug(logger, "auth_token_validated", player_id=player_id, username=row["username"])

    return {"player_id": player_id, "username": row["username"], "token": credentials.credentials}


PlayerDep = Annotated[dict, Depends(get_current_player)]


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/redeem", tags=["auth"], responses={400: {"description": "Username already in use or invalid invite"}})
async def redeem_invite(body: RedeemInviteRequest, conn: DbDep) -> TokenResponse:
    """Redeems an invite code and creates an account."""
    player_id = str(uuid.uuid4())
    log_flow(
        logger,
        "auth_redeem_attempt",
        username=body.username,
        invite_code=mask_secret(body.invite_code),
    )

    # Check whether the username already exists
    existing = await state_manager.get_player_by_username(conn, body.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already in use")

    # Resgata invite
    redeemed = await state_manager.redeem_invite(conn, body.invite_code, player_id)
    if not redeemed:
        raise HTTPException(status_code=400, detail="Invalid or already used invite code")

    # Create player
    password_hash = hash_password(body.password)
    await state_manager.create_player(conn, player_id, body.username, password_hash)

    token = create_token(player_id, body.username)
    log_flow(logger, "auth_redeem_success", player_id=player_id, username=body.username)
    return TokenResponse(access_token=token)


@app.post("/auth/login", tags=["auth"], responses={401: {"description": "Invalid credentials"}})
async def login(body: LoginRequest, conn: DbDep) -> TokenResponse:
    """Login with username/password."""
    log_flow(logger, "auth_login_attempt", username=body.username)
    row = await state_manager.get_player_by_username(conn, body.username)
    if row is None:
        logger.warning("Login: user '%s' not found", body.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, row["password_hash"]):
        computed = hash_password(body.password)
        logger.warning(
            "Login: hash mismatch for '%s' | stored=%s... computed=%s...",
            body.username, row["password_hash"][:10], computed[:10],
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(row["player_id"], body.username)
    log_flow(logger, "auth_login_success", player_id=row["player_id"], username=body.username)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Character routes
# ---------------------------------------------------------------------------

@app.post("/character", tags=["character"], responses={400: {"description": "Character already created"}})
async def create_character(
    body: CreateCharacterRequest,
    player: PlayerDep,
    conn: DbDep,
) -> CharacterResponse:
    """Creates a character and triggers the isekai convocation."""
    player_id = player["player_id"]

    # Check whether the player already has a character
    row = await state_manager.get_player_by_id(conn, player_id)
    if row and row["name"]:
        raise HTTPException(status_code=400, detail="Character already created")

    # GM infers class and generates a secret objective (Phase 1: simplified)
    inferred_class = await _infer_class_from_backstory_local(body.backstory, body.faction.value)
    secret_objective = _generate_secret_objective(body.faction.value)
    max_hp = 100  # base VIT=10

    await state_manager.set_character(
        conn,
        player_id=player_id,
        name=body.name,
        race=body.race.value,
        faction=body.faction.value,
        backstory=body.backstory,
        inferred_class=inferred_class,
        secret_objective=secret_objective,
        max_hp=max_hp,
    )
    await state_manager.seed_starter_inventory(conn, player_id, body.backstory)
    await state_manager.ensure_default_world_state(conn)
    mission_state = await state_manager.initialize_or_refresh_cooperative_mission(conn)
    log_flow(
        logger,
        "character_created",
        player_id=player_id,
        name=body.name,
        race=body.race.value,
        faction=body.faction.value,
        inferred_class=inferred_class,
        cooperative_mission_active=mission_state.get("cooperative_mission_active"),
    )

    return CharacterResponse(
        player_id=player_id,
        name=body.name,
        race=body.race.value,
        faction=body.faction.value,
        inferred_class=inferred_class,
        level=1,
        attributes={"strength": 10, "dexterity": 10, "intelligence": 10,
                    "vitality": 10, "luck": 10, "charisma": 10},
        status="alive",
        secret_objective=secret_objective,
    )


@app.get("/character", tags=["character"], responses={404: {"description": "Character not found"}})
async def get_character(player: PlayerDep, conn: DbDep) -> CharacterResponse:
    """Returns current character data."""
    import json
    row = await state_manager.get_player_by_id(conn, player["player_id"])
    if row is None or not row["name"]:
        raise HTTPException(status_code=404, detail="Character not found")

    attrs = json.loads(row["attributes_json"] or "{}")
    log_debug(
        logger,
        "character_loaded",
        player_id=row["player_id"],
        level=row["level"],
        status=row["status"],
    )
    return CharacterResponse(
        player_id=row["player_id"],
        name=row["name"],
        race=row["race"],
        faction=row["faction"],
        inferred_class=row["inferred_class"],
        level=row["level"],
        attributes=attrs,
        status=row["status"],
    )


@app.get("/character/macros", tags=["character"])
async def get_character_macros(player: PlayerDep, conn: DbDep) -> dict:
    macros = await state_manager.get_character_macros(conn, player["player_id"])
    log_debug(logger, "character_macros_loaded", player_id=player["player_id"], count=len(macros))
    return {"macros": macros}


@app.put("/character/macros", tags=["character"], responses={400: {"description": "Invalid macros"}})
async def update_character_macros(body: UpdateMacrosBody, player: PlayerDep, conn: DbDep) -> dict:
    normalized: list[dict[str, str]] = []
    for macro in body.macros:
        name = macro.name.strip()
        template = macro.template.strip()
        if not name.startswith("/") or not template:
            raise HTTPException(status_code=400, detail="Invalid macros")
        normalized.append({"name": name, "template": template})

    await state_manager.set_character_macros(conn, player["player_id"], normalized)
    log_flow(logger, "character_macros_updated", player_id=player["player_id"], count=len(normalized))
    return {"status": "updated", "macros": normalized}


@app.put("/character/backstory", tags=["character"], responses={400: {"description": "Invalid backstory"}})
async def update_character_backstory(body: UpdateBackstoryBody, player: PlayerDep, conn: DbDep) -> dict:
    backstory = body.backstory.strip()
    if len(backstory) < 10:
        raise HTTPException(status_code=400, detail="Invalid backstory")
    await state_manager.update_backstory(conn, player["player_id"], backstory)
    log_flow(
        logger,
        "character_backstory_updated",
        player_id=player["player_id"],
        length=len(backstory),
        preview=clip_text(backstory, 120),
    )
    await cm.manager.broadcast({
        "type": "gm_thinking",
        "message": "The GM detected a backstory update and is re-evaluating the context.",
    })
    return {"status": "updated"}


@app.get("/character/spell-aliases", tags=["character"])
async def get_character_spell_aliases(player: PlayerDep, conn: DbDep) -> dict:
    aliases = await state_manager.get_spell_aliases(conn, player["player_id"])
    log_debug(logger, "spell_aliases_loaded", player_id=player["player_id"], count=len(aliases))
    return {"aliases": aliases}


@app.put("/character/spell-aliases", tags=["character"])
async def update_character_spell_aliases(body: UpdateSpellAliasesBody, player: PlayerDep, conn: DbDep) -> dict:
    normalized: dict[str, str] = {}
    for base_name, alias in body.aliases.items():
        key = base_name.strip().lower()
        value = alias.strip()
        if not key or not value:
            continue
        normalized[key] = value
    await state_manager.set_spell_aliases(conn, player["player_id"], normalized)
    log_flow(logger, "spell_aliases_updated", player_id=player["player_id"], count=len(normalized))
    return {"status": "updated", "aliases": normalized}


@app.get("/debug/state", tags=["debug"], responses={404: {"description": PLAYER_NOT_FOUND_DETAIL}})
async def get_debug_state_snapshot(player: PlayerDep, conn: DbDep) -> dict:
    player_id = player["player_id"]
    row = await state_manager.get_player_by_id(conn, player_id)
    if row is None:
        raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND_DETAIL)

    current_turn = await state_manager.get_current_turn_number(conn)
    tension_level = await state_manager.get_world_state(conn, "tension_level")
    current_location = await state_manager.get_world_state(conn, "current_location")
    campaign_paused = await state_manager.get_world_state(conn, "campaign_paused")

    quest_flags: dict[str, str] = {}
    async with conn.execute(
        "SELECT flag_key, flag_value FROM quest_flags ORDER BY updated_at DESC LIMIT 20"
    ) as cursor:
        for record in await cursor.fetchall():
            quest_flags[record["flag_key"]] = record["flag_value"]

    async with conn.execute("SELECT COUNT(*) AS c FROM history") as cursor:
        history_count = int((await cursor.fetchone())["c"])
    async with conn.execute("SELECT COUNT(*) AS c FROM players") as cursor:
        players_count = int((await cursor.fetchone())["c"])

    async with conn.execute(
        "SELECT role, content, turn_number FROM history ORDER BY turn_number DESC, created_at DESC LIMIT 5"
    ) as cursor:
        history_rows = await cursor.fetchall()

    recent_history = [
        {
            "turn_number": h["turn_number"],
            "role": h["role"],
            "content_preview": clip_text(h["content"], 180),
        }
        for h in reversed(history_rows)
    ]

    runtime_metrics = game_master.get_runtime_metrics()
    alive_players = await state_manager.get_all_alive_players(conn)
    party_size = len([p for p in alive_players if p["name"]])
    scaling_preview = game_master.get_encounter_scaling_preview(party_size)
    snapshot = {
        "server_time": time.time(),
        "db_path": os.getenv("DATABASE_PATH", "aerus.db"),
        "player": {
            "player_id": row["player_id"],
            "username": row["username"],
            "name": row["name"],
            "faction": row["faction"],
            "inferred_class": row["inferred_class"],
            "level": row["level"],
            "status": row["status"],
            "current_hp": row["current_hp"],
            "max_hp": row["max_hp"],
            "current_mp": row["current_mp"],
            "max_mp": row["max_mp"],
            "current_stamina": row["current_stamina"],
            "max_stamina": row["max_stamina"],
            "inventory_weight": row["inventory_weight"],
            "weight_capacity": row["weight_capacity"],
            "secret_objective_preview": clip_text(row["secret_objective"] or "", 120),
        },
        "world_state": {
            "current_turn": current_turn,
            "tension_level": int(tension_level) if str(tension_level or "").isdigit() else tension_level,
            "current_location": current_location,
            "campaign_paused": campaign_paused,
        },
        "quest_flags": quest_flags,
        "recent_history": recent_history,
        "runtime": {
            "connected_players": cm.manager.connected_count(),
            "connected_player_ids": cm.manager.connected_player_ids(),
            "history_rows": history_count,
            "players_rows": players_count,
            "alive_players": party_size,
            "encounter_scale_preview": scaling_preview["encounter_scale"],
            "boss_scale_steps_preview": scaling_preview["boss_scale_steps"],
            **runtime_metrics,
        },
    }
    log_debug(
        logger,
        "debug_snapshot_generated",
        player_id=player_id,
        current_turn=current_turn,
        connected_players=snapshot["runtime"]["connected_players"],
    )
    return snapshot


# ---------------------------------------------------------------------------
# BYOK route
# ---------------------------------------------------------------------------

@app.post("/player/byok", tags=["player"])
async def register_byok(
    body: RegisterByokKeyRequest,
    player: PlayerDep,
    conn: DbDep,
) -> dict:
    """Register or update the player's OpenRouter key (BYOK)."""
    encrypted = encrypt_api_key(body.openrouter_api_key)
    await state_manager.set_byok_key(conn, player["player_id"], encrypted)
    log_flow(
        logger,
        "byok_registered",
        player_id=player["player_id"],
        key_preview=mask_secret(body.openrouter_api_key),
    )
    return {"message": "Key registered successfully"}


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.post(
    "/admin/invite",
    tags=["admin"],
    responses={403: {"description": "Access denied"}},
)
async def create_invite_code(request: Request, conn: DbDep) -> dict:
    """Generate an invite code. Protected by ADMIN_SECRET when configured."""
    admin_secret = os.getenv("ADMIN_SECRET")
    if admin_secret and request.headers.get("X-Admin-Secret") != admin_secret:
        raise HTTPException(status_code=403, detail="Access denied")
    code = generate_invite_code()
    await state_manager.create_invite(conn, code, created_by="admin")
    log_flow(logger, "admin_invite_created", invite_code=mask_secret(code))
    return {"invite_code": code}


@app.post(
    "/gm/dice/request",
    tags=["gm"],
    responses={404: {"description": "Player not found"}},
)
async def request_manual_dice_roll(body: DiceRollRequestBody, conn: DbDep) -> dict:
    """The GM requests a manual dice roll from a player."""
    roll_id = str(uuid.uuid4())
    row = await state_manager.get_player_by_id(conn, body.player_id)
    if row is None:
        raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND_DETAIL)

    await state_manager.create_dice_roll_request(
        conn,
        roll_id=roll_id,
        player_id=body.player_id,
        roll_type=body.roll_type,
        dc=body.dc,
        description=body.description,
    )

    await cm.manager.send_to(body.player_id, {
        "type": WSMessageType.REQUEST_DICE_ROLL,
        "roll_id": roll_id,
        "roll_type": body.roll_type,
        "dc": body.dc,
        "description": body.description,
    })

    log_flow(
        logger,
        "dice_request_created",
        roll_id=roll_id,
        player_id=body.player_id,
        roll_type=body.roll_type,
        dc=body.dc,
    )

    return {"roll_id": roll_id, "status": "requested"}


@app.post(
    "/dice/submit",
    tags=["dice"],
    responses={400: {"description": "Invalid roll or already submitted"}},
)
async def submit_manual_dice_roll(body: DiceRollSubmitBody, player: PlayerDep, conn: DbDep) -> dict:
    """Player submits the result plus a single circumstance argument."""
    ok = await state_manager.submit_dice_roll_result(
        conn,
        roll_id=body.roll_id,
        player_id=player["player_id"],
        initial_roll=body.initial_roll,
        initial_result=body.initial_result,
        argument=body.argument,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid roll or argument already submitted")

    record = await state_manager.get_dice_roll_request(conn, body.roll_id)
    if record:
        await cm.manager.broadcast({
            "type": "dice_argument_submitted",
            "roll_id": body.roll_id,
            "player_id": player["player_id"],
            "initial_roll": body.initial_roll,
            "initial_result": body.initial_result,
            "argument": record["argument"],
            "description": record["description"],
        })

    log_flow(
        logger,
        "dice_result_submitted",
        roll_id=body.roll_id,
        player_id=player["player_id"],
        initial_roll=body.initial_roll,
        initial_result=body.initial_result,
    )

    return {"status": "submitted"}


@app.post(
    "/gm/dice/resolve",
    tags=["gm"],
    responses={
        400: {"description": "Invalid verdict"},
        404: {"description": "Roll not found"},
    },
)
async def resolve_manual_dice_roll(body: DiceRollResolveBody, conn: DbDep) -> dict:
    """The GM resolves the roll with the final decision."""
    allowed = {"accept_with_bonus", "accept_no_bonus", "reject", "reroll_requested"}
    if body.verdict not in allowed:
        raise HTTPException(status_code=400, detail="Invalid verdict")

    row = await state_manager.resolve_dice_roll(
        conn,
        roll_id=body.roll_id,
        verdict=body.verdict,
        circumstance_bonus=body.circumstance_bonus,
        explanation=body.explanation,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Roll not found")

    await cm.manager.send_to(row["player_id"], {
        "type": WSMessageType.DICE_ROLL_RESOLVED,
        "roll_id": body.roll_id,
        "verdict": row["verdict"],
        "circumstance_bonus": row["circumstance_bonus"],
        "final_result": row["final_result"],
        "explanation": row["explanation"],
    })

    log_flow(
        logger,
        "dice_result_resolved",
        roll_id=body.roll_id,
        player_id=row["player_id"],
        verdict=row["verdict"],
        final_result=row["final_result"],
    )

    return {"status": "resolved", "roll_id": body.roll_id}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str) -> None:
    """Per-player WebSocket endpoint. JWT token is passed in the URL."""
    player_id, username = _validate_ws_token(token)
    if not player_id:
        log_flow(logger, "ws_rejected", token=mask_secret(token))
        await websocket.close(code=4001, reason="Invalid token")
        return

    log_flow(logger, "ws_connect_attempt", player_id=player_id, username=username)
    await cm.manager.connect(websocket, player_id, username)
    await _post_connect_setup(player_id, username, token)

    try:
        while True:
            data = await websocket.receive_json()
            await _handle_ws_message(data, player_id, username)
    except WebSocketDisconnect:
        cm.manager.disconnect(player_id)
        log_flow(logger, "ws_disconnected", player_id=player_id, username=username)


def _validate_ws_token(token: str) -> tuple[str, str]:
    try:
        payload = decode_token(token)
        return payload["sub"], payload["username"]
    except (JWTError, KeyError):
        return "", ""


async def _maybe_refresh_ws_token(player_id: str, username: str, token: str) -> None:
    if not should_refresh_token(token):
        return

    new_token = create_token(player_id, username)
    await cm.manager.send_to(player_id, {
        "type": WSMessageType.TOKEN_REFRESH,
        "access_token": new_token,
    })
    log_debug(logger, "ws_token_refreshed", player_id=player_id, username=username)


async def _load_world_sync_snapshot(conn: aiosqlite.Connection) -> dict:
    tension_level = await state_manager.get_world_state(conn, "tension_level") or "5"
    current_location = await state_manager.get_world_state(conn, "current_location") or state_manager.DEFAULT_START_LOCATION
    campaign_paused = await state_manager.get_world_state(conn, "campaign_paused") or "0"
    cooperative = await state_manager.get_cooperative_mission_state(conn)
    travel = await travel_manager.get_travel_state(conn)
    return {
        "current_location": current_location,
        "tension_level": int(tension_level) if str(tension_level).isdigit() else 5,
        "campaign_paused": campaign_paused == "1",
        "quest_flags": cooperative,
        "travel": travel,
    }


async def _load_player_sync_snapshot(player_id: str) -> tuple[dict | None, list, list, list, dict]:
    async with state_manager.db_context() as conn:
        await state_manager.ensure_default_world_state(conn)
        await state_manager.initialize_or_refresh_cooperative_mission(conn)
        row = await state_manager.get_player_by_id(conn, player_id)
        if not row or not row["name"]:
            return None, [], [], [], {}
        inv_rows = await state_manager.get_player_inventory(conn, player_id)
        cond_rows = await state_manager.get_player_conditions(conn, player_id)
        history_rows = await state_manager.get_recent_history(conn, limit=20)
        world_state = await _load_world_sync_snapshot(conn)
    return dict(row), inv_rows, cond_rows, history_rows, world_state


def _build_player_full_state(row: dict, inv_rows: list, cond_rows: list) -> dict:
    attrs = json.loads(row["attributes_json"] or "{}")
    currency = json.loads(
        row["currency_json"] or '{"copper":0,"silver":5,"gold":0,"platinum":0}'
    )
    inventory = [
        {
            "item_id": r["item_id"],
            "name": r["name"],
            "description": r["description"],
            "rarity": r["rarity"],
            "quantity": r["quantity"],
            "equipped": bool(r["equipped"]),
        }
        for r in inv_rows
    ]
    conditions = [
        {
            "condition_id": r["condition_id"],
            "name": r["name"],
            "description": r["description"],
            "duration_turns": r["duration_turns"],
            "applied_at_turn": r["applied_at_turn"],
            "is_buff": bool(r["is_buff"]),
        }
        for r in cond_rows
    ]

    return {
        "player_id": row["player_id"],
        "name": row["name"],
        "race": row["race"],
        "faction": row["faction"],
        "backstory": row["backstory"],
        "inferred_class": row["inferred_class"],
        "level": row["level"],
        "experience": row["experience"],
        "experience_next": row["level"] * 100,
        "current_hp": row["current_hp"],
        "max_hp": row["max_hp"],
        "current_mp": row["current_mp"],
        "max_mp": row["max_mp"],
        "current_stamina": row["current_stamina"],
        "max_stamina": row["max_stamina"],
        "status": row["status"],
        "attributes": attrs,
        "inventory": inventory,
        "conditions": conditions,
        "currency": currency,
        "inventory_weight": row["inventory_weight"],
        "weight_capacity": row["weight_capacity"],
        "passive_milestones": json.loads(row["milestones_json"] or "[]"),
        "magic_proficiency": json.loads(row["magic_prof_json"] or "{}"),
        "weapon_proficiency": json.loads(row["weapon_prof_json"] or "{}"),
        "macros": json.loads(row["macros_json"] or "[]"),
        "spell_aliases": json.loads(row["spell_aliases_json"] or "{}"),
        "secret_objective": row["secret_objective"] or "",
    }


async def _send_player_full_sync(player_id: str, state: dict, world_state: dict) -> None:
    await cm.manager.send_to(player_id, {
        "type": "full_state_sync",
        "state": state,
        "world_state": world_state,
    })


async def _send_player_history_sync(player_id: str, history_rows: list) -> None:
    if not history_rows:
        return
    await cm.manager.send_to(player_id, {
        "type": WSMessageType.HISTORY_SYNC,
        "entries": [{"role": r["role"], "content": r["content"]} for r in history_rows],
    })


def _schedule_isekai_convocation(player_id: str, row: dict) -> None:
    task = asyncio.create_task(_trigger_isekai_on_connect(player_id, row))
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)


async def _post_connect_setup(player_id: str, username: str, token: str) -> None:
    """Refresh token, sync state, and trigger the isekai convocation on connect."""
    await _maybe_refresh_ws_token(player_id, username, token)

    row, inv_rows, cond_rows, history_rows, world_state = await _load_player_sync_snapshot(player_id)
    if not row:
        return

    full_state = _build_player_full_state(row, inv_rows, cond_rows)
    await _send_player_full_sync(player_id, full_state, world_state)
    await _send_player_history_sync(player_id, history_rows)

    log_flow(
        logger,
        "ws_post_connect_sync",
        player_id=player_id,
        username=username,
        has_character=bool(row["name"]),
        inventory_count=len(full_state["inventory"]),
        conditions_count=len(full_state["conditions"]),
        history_count=len(history_rows),
        convocation_pending=bool(not row["convocation_sent"]),
        location=world_state.get("current_location"),
        cooperative_mission_active=world_state.get("quest_flags", {}).get("cooperative_mission_active"),
    )

    if not row["convocation_sent"]:
        await cm.manager.send_to(player_id, {
            "type": WSMessageType.GM_THINKING,
            "message": "The GM is preparing your arrival into the world of Aerus...",
        })
        _schedule_isekai_convocation(player_id, row)


async def _handle_ws_message(data: dict, player_id: str, username: str) -> None:
    msg_type = data.get("type", "action")

    if msg_type == "ping":
        log_debug(logger, "ws_ping", player_id=player_id)
        return

    if msg_type in ("action", ""):
        action_text = data.get("action", data.get("text", "")).strip()
        if not action_text:
            log_debug(logger, "ws_action_ignored_empty", player_id=player_id)
            return
        if len(action_text) > 1000:
            await cm.manager.send_to(player_id, {
                "type": WSMessageType.ERROR,
                "message": "Action too long (max. 1000 chars)",
            })
            log_flow(logger, "ws_action_rejected_too_long", player_id=player_id, length=len(action_text))
            return
        async with state_manager.db_context() as conn:
            row = await state_manager.get_player_by_id(conn, player_id)
        player_name = row["name"] if row and row["name"] else username
        log_flow(
            logger,
            "ws_action_received",
            player_id=player_id,
            player_name=player_name,
            action_preview=clip_text(action_text, 140),
            length=len(action_text),
        )
        await game_master.submit_action(player_id, player_name, action_text)
        return

    if msg_type == "dice_result":
        # Future: handle dice result submission via WS instead of HTTP
        return

    logger.debug("WS msg type '%s' from %s - no handler", msg_type, player_id)


# ---------------------------------------------------------------------------
# Helpers (simple Phase 1 logic - will move to game_master in Phase 2)
# ---------------------------------------------------------------------------

def _infer_class_from_backstory_keyword(backstory: str, faction: str) -> str:
    """Deterministic keyword-based fallback."""
    backstory_lower = backstory.lower()
    if any(w in backstory_lower for w in ["magic", "spell", "arcane", "study"]):
        return "Mage"
    if any(w in backstory_lower for w in ["sword", "warrior", "battle", "combat"]):
        return "Warrior"
    if any(w in backstory_lower for w in ["shadow", "thief", "stealth", "sneak"]):
        return "Rogue"
    if any(w in backstory_lower for w in ["healing", "faith", "divine", "sacred"]):
        return "Cleric"
    if any(w in backstory_lower for w in ["bow", "hunt", "forest", "nature"]):
        return "Ranger"

    faction_defaults = {
        "church_pure_flame": "Paladin",
        "empire_valdrek": "Soldier",
        "guild_of_threads": "Arcanist",
        "children_of_broken_thread": "Thread Weaver",
    }
    return faction_defaults.get(faction, "Adventurer")


async def _infer_class_from_backstory_local(backstory: str, faction: str) -> str:
    allowed_classes = [
        "Mage",
        "Warrior",
        "Rogue",
        "Cleric",
        "Ranger",
        "Paladin",
        "Arcanist",
        "Soldier",
        "Thread Weaver",
        "Adventurer",
    ]
    system_prompt = (
        "You analyze RPG backstories and infer an initial class. "
        "Reply with ONLY valid JSON: {\"inferred_class\": \"...\", \"rationale\": \"...\"}."
    )
    user_prompt = (
        f"Backstory:\n{backstory[:1200]}\n\n"
        f"Faction: {faction}\n"
        f"Allowed classes: {', '.join(allowed_classes)}\n"
        "Choose one allowed class based on the narrative profile."
    )

    model = os.getenv("AERUS_OLLAMA_BACKSTORY_MODEL", "qwen2.5:14b-instruct")
    try:
        raw = await generate_text(
            system_prompt,
            user_prompt,
            max_tokens=120,
            model_override=model,
        )
        parsed = json.loads(_extract_json_body(raw))
        inferred = str(parsed.get("inferred_class", "")).strip()
        if inferred in allowed_classes:
            log_flow(
                logger,
                "class_inference_local_success",
                faction=faction,
                inferred_class=inferred,
                rationale=clip_text(str(parsed.get("rationale", "")), 120),
            )
            return inferred
    except Exception as exc:
        logger.warning("Keyword-based class inference fallback: %s", exc)

    log_flow(logger, "class_inference_fallback", faction=faction)
    return _infer_class_from_backstory_keyword(backstory, faction)


def _extract_json_body(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else text


def _generate_secret_objective(faction_id: str) -> str:
    """Phase 1: hardcoded secret objectives. Phase 2: generated dynamically by the GM."""
    objectives = {
        "church_pure_flame": (
            "Locate and destroy any evidence that the Church knew Vor'Athek was real "
            "before the Sealing. The people's faith must remain unshaken."
        ),
        "empire_valdrek": (
            "Recover at least 3 Aeridian Fragments and return them to the Kael Archive "
            "before the Guild of Threads can catalog them. Valdrek's magical monopoly depends on it."
        ),
        "guild_of_threads": (
            "Confirm that the Last Chamber exists and contains the instructions for the Complete Sealing. "
            "This knowledge cannot fall into the hands of the Church or the Empire."
        ),
        "children_of_broken_thread": (
            "Find the Weaver or someone who knows where to find them. "
            "The restoration of the Broken Thread begins here, whatever the cost."
        ),
    }
    return objectives.get(faction_id, "Survive and uncover the truth about Aerus.")


async def _send_isekai_convocation(
    player_id: str,
    body: CreateCharacterRequest,
    secret_objective: str,
) -> None:
    """Generate and send the isekai convocation narrative (background task)."""
    try:
        log_flow(logger, "isekai_convocation_prepare", player_id=player_id, faction=body.faction.value)
        # Wait for the player to connect through WebSocket (max 60s)
        for _ in range(60):
            if cm.manager.is_connected(player_id):
                break
            await asyncio.sleep(1)
        else:
            logger.warning("Isekai convocation: player %s did not connect within 60s", player_id)
            return

        async with state_manager.db_context() as conn:
            narrative = await game_master.generate_isekai_convocation(
                conn,
                player_id,
                player_name=body.name,
                race=body.race.value,
                faction=body.faction.value,
                backstory=body.backstory,
            )
        await cm.manager.send_isekai_convocation(
            player_id,
            narrative=narrative,
            faction=body.faction.value,
            secret_objective=secret_objective,
        )
        log_flow(logger, "isekai_convocation_sent", player_id=player_id, faction=body.faction.value)
    except Exception as e:
        logger.exception("Error during isekai convocation for %s: %s", player_id, e)


async def _trigger_isekai_on_connect(player_id: str, row: dict) -> None:
    """
    Triggered on WebSocket connect when convocation_sent == 0.
    Generates and sends the convocation using data already loaded from the database.
    """
    try:
        log_flow(logger, "isekai_on_connect_start", player_id=player_id, faction=row["faction"])
        async with state_manager.db_context() as conn:
            narrative = await game_master.generate_isekai_convocation(
                conn,
                player_id,
                player_name=row["name"],
                race=row["race"],
                faction=row["faction"],
                backstory=row["backstory"] or "",
            )
            await state_manager.mark_convocation_sent(conn, player_id)

        await cm.manager.send_isekai_convocation(
            player_id,
            narrative=narrative,
            faction=row["faction"],
            secret_objective=row["secret_objective"] or "",
        )
        log_flow(logger, "isekai_on_connect_sent", player_id=player_id, faction=row["faction"])
    except Exception as e:
        logger.exception("Error in _trigger_isekai_on_connect for %s: %s", player_id, e)







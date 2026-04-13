# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

Aerus is a multiplayer cooperative narrative RPG with a FastAPI backend (WebSocket + HTTP) and a React frontend.

- Backend: turn orchestration, state persistence, LLM context assembly, game events.
- Frontend: player experience, narrative streaming, state synchronization, combat and narrative UI.

## Useful Commands

### Backend

```bash
# Start server with hot-reload
cd backend && .venv/Scripts/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

# Run all unit tests
cd backend && .venv/Scripts/python -m pytest tests/ -v

# Run a specific test
cd backend && .venv/Scripts/python -m pytest tests/test_state_manager.py -v

# Run E2E tests (Playwright — requires active server)
cd backend && .venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v -s
```

### Frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
npm run build
npm test          # Vitest (unit tests)
```

### Makefile (shortcuts)

```bash
make setup        # Create venv + install dependencies
make full-dev     # Backend + frontend in parallel
make test         # Run pytest
make clean        # Remove aerus.db, chroma_db, caches
make sync-lore    # Sync lore/ to backend/config/ and invalidate chroma_db
```

## Backend Architecture

### Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API/Transport | `src/main.py` | HTTP and WebSocket routes, middleware, lifespan |
| Application | `src/application/` | Use-case orchestration (e.g. billing) |
| Infrastructure | `src/infrastructure/` | Config loader, external integrations |
| Core (legacy, migrating) | `src/*.py` | game_master, state_manager, context_builder… |

**Strict rules:**
- Zero business logic in `main.py`
- SQL exclusively in `state_manager.py`
- ChromaDB exclusively in `vector_store.py`
- Preserve public import compatibility when migrating modules to `application/` or `infrastructure/`

### Core Modules

- **`game_master.py`** — orchestrates turns (3s batch), selects model by tension level, parses events.
- **`state_manager.py`** — 14 SQLite tables (WAL mode required), applies state deltas, auto level-up.
- **`context_builder.py`** — 4 context layers (L0 kernel ~200 tok, L1 campaign ~170, L2 state ~400, L3 history ~1500) + memory (~200) + lore retrieval (~800).
- **`billing_router.py`** and `application/billing/billing_router.py` — BYOK vs. admin key routing by tension.
- **`vector_store.py`** — ingests bestiary.md + world.md (by section) into ChromaDB at startup, semantic search for lore and creatures.
- **`connection_manager.py`** — manages WebSocket rooms, token-by-token streaming, heartbeat.
- **`ws_contracts.py`** — Pydantic schemas for all outbound WebSocket message types. **Single source of truth for the WS contract**; the frontend Zod schemas in `frontend/src/types/wsSchemas.ts` must mirror this file.
- **`travel_manager.py`** — reads routes/locations from `travel.yaml`, rolls daily encounters (d20 ± terrain/tension), drives `start_travel` / `advance_travel_day` / `complete_travel`.
- **`behavior_trajectory.py`** — scores player episodes by action category; drives class mutation path selection at levels 25/50/75/100.
- **`memory_manager.py`** — assigns importance scores to episodic events for selective LLM context injection.
- **`reputation_gates.py`** — fires one-shot faction unlock events when a player crosses thresholds defined in `config/reputation_gates.yaml`; guards via `quest_flags` to prevent re-firing.
- **`rumor_manager.py`** — injects faction-biased rumor variants per player into L2 context once per `rumor_id`; new rumors surface as world tension crosses `tension_min`.
- **`time_manager.py`** — persists Ash Calendar state (3 seasons × 90 days = 270-day year, starting year 4217 PC) via `world_state` table.
- **`inventory_manager.py`** — weight/carrying-capacity checks and copper→silver→gold→platinum currency conversion.
- **`recipe_manager.py`** — loads crafting recipes from `config/recipes.yaml` at startup.
- **`summarizer.py`** — LLM-based summarization of recent conversation history for memory injection.
- **`models.py`** — shared Pydantic/dataclass contracts between modules (`ActionBatch`, `GMResponse`, `Faction`, etc.). No raw dicts for cross-module communication.
- **`migration_runner.py`** — applies sequential SQL migrations from `backend/migrations/` at server startup (currently 11 migrations).

### Deployment Constraint

`fly.toml` sets `max_machines = 1`. Sharding requires PostgreSQL migration before scaling.

## Frontend Architecture

### Hybrid Organization

- `pages/*` — screen composition (LoginPage, CharacterCreationPage, GamePage)
- `features/game/` — barrel re-export of all game components; pages should import via `features/` when available
- `components/*` — components by domain (`character/`, `combat/`, `narrative/`, `screens/`, `travel/`, `ui/`)
- `store/gameStore.ts` — Zustand, single source of truth for game state
- `hooks/useWebSocket.ts` — manages WS connection and message dispatch
- `api/http.ts` — fetch wrappers for REST endpoints
- `i18n/` — i18next setup; supported locales are English (`en.json`) and Portuguese (`pt.json`)
- `types/wsContracts.ts` — Zod schemas mirroring `backend/src/ws_contracts.py`; keep in sync when WS message types change

## Lore and Configuration

- `lore/` = canonical authorial source (`world.md`, `bestiary.md`)
- `backend/config/` = operational copy used at runtime by the server
- `backend/config/world_kernel.md` = compact world summary (~200 tokens), injected as L0 static in every GM call
- **When editing lore, sync to `backend/config/` before validating in-game behavior** (use `make sync-lore`)
- **When editing `world.md` or any `bestiary_tN.md`, delete `backend/chroma_db/` to force re-ingestion on next startup**
- `backend/config/bestiary_t{1-5}.md` = bestiary split by tier (Tier 1-5). `bestiary.md` is the index only.
- `backend/config/campaign.yaml` controls: `max_players`, `darkness_level`, `permadeath`, LLM model selection, token budget per layer, mechanics (batch window, history turns, level cap)

## Environment Variables

Backend (`.env`): `OPENROUTER_API_KEY`, `FERNET_KEY`, `JWT_SECRET`, `OLLAMA_BASE_URL`, `CHROMA_DB_PATH`, `LOG_LEVEL`

Frontend (`.env.local`): `VITE_API_URL`

## Local Artifacts (do not version)

`backend/.venv`, `backend/aerus.db`, `backend/chroma_db`, `frontend/node_modules`, `frontend/dist`

## GM Evaluation

The `backend/eval/` directory contains a modular behavioral evaluator for GM response quality.

```bash
# Run all eval scenarios
cd backend && .venv/Scripts/python eval/gm_eval.py

# Key env vars:
# AERUS_EVAL_TIER=core|extended|all
# AERUS_EVAL_SCENARIOS=1,3        (specific scenario indexes)
# AERUS_EVAL_CONCURRENCY=2        (parallel scenarios)
# AERUS_EVAL_MAX_TOKENS=600       (override GM response budget)
```

Modules: `gm_eval.py` (orchestrator) → `gm_eval_runtime.py` (scenario execution) → `gm_eval_assertions.py` (scoring dimensions + hard-fail labels) → `gm_eval_reporting.py` (output). Scenario definitions live in `eval/topics/`.

## Sources of Truth

- **Main index**: `docs/aerus_rpg_bible.md` — lists all documents and their contents
- Frontend specification: `docs/FRONTEND_SPEC.md`
- Implementation status: `docs/IMPLEMENTATION.md`

### Lore (split by theme)
- Cosmology + history: `docs/aerus_lore_cosmology_history.md`
- Geography: `docs/aerus_lore_geography.md`
- Factions + The Dome: `docs/aerus_lore_dome_factions.md`
- Geopolitics + events + economy: `docs/aerus_lore_geopolitics_economy.md`

### Mechanics (split by theme)
- Magic + isekai: `docs/aerus_mechanics_magic_isekai.md`
- Races: `docs/aerus_mechanics_races.md`
- Seals + reputation + rumors: `docs/aerus_mechanics_systems.md`
- Languages + crafting: `docs/aerus_mechanics_languages_crafting.md`

### Classes, NPCs, Missions
- Base classes (8 classes): `docs/aerus_base_classes.md`
- Formal mutations (levels 25/50/75/100): `docs/aerus_class_mutations.md`
- Main NPCs: `docs/aerus_main_npcs.md`
- Expanded NPC sheets: `docs/aerus_npc_sheets.md`
- GM Guide: `docs/aerus_gm_guide.md`
- Missions by faction + arcs: `docs/campaign_missions_*.md`
- Travel and encounter system: `docs/aerus_travel.md`

### Technical Context (split)
- Overview + stack: `docs/PROJECT_CONTEXT_overview_stack.md`
- Architecture + ARD: `docs/PROJECT_CONTEXT_architecture_ard.md`
- ADRs + SDD: `docs/PROJECT_CONTEXT_adrs_sdd.md`
- Rules + roadmap: `docs/PROJECT_CONTEXT_rules_roadmap.md`

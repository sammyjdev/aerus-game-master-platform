# Aerus RPG - Implementation Status

> Updated on March 25, 2026.
> This document summarizes the current implementation status against the project specification and the active runtime architecture.

---

## Executive Summary

The project is in a strong portfolio-ready state. The backend gameplay loop, WebSocket flow, world state persistence, lore/config pipeline, and core frontend experience are implemented. A second round of improvements (March 2026) added episodic memory, behavioral mutation tracking, asymmetric faction rumors, reputation gates, tension-driven world state, versioned schema migrations, and a GM admin dashboard.

### Status Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Backend runtime | Implemented | Local-first game loop, event dispatch, persistence, auth, billing, retrieval |
| Frontend app | Implemented | Login, character creation, game UI, BYOK, audio, travel, event flow, admin dashboard |
| Config and lore | Implemented | Canonical world, campaign, items, bestiary, rumors, and reputation gates |
| Schema migrations | Implemented | Versioned SQL files in `backend/migrations/`, runner in `migration_runner.py` |
| WS contracts | Implemented | Pydantic schemas (`ws_contracts.py`) + Zod schemas (`wsContracts.ts`) |
| Episodic memory | Implemented | Per-player `player_episodes` table, injected into L2 context |
| Behavioral mutations | Implemented | `behavior_trajectory.py` maps dominant playstyle to mutation path |
| Tension system | Implemented | Tension drives L1 narrative directive + L2 faction world-state signal |
| Reputation gates | Implemented | `reputation_gates.yaml` + gate events on threshold crossing |
| Asymmetric rumors | Implemented | `rumors.yaml` with faction-biased variants, per-player delivery tracking |
| GM admin dashboard | Implemented | React `AdminPage` at `/admin` — player list, pause/resume, invite generation |
| Lore sync | Implemented | `make sync-lore` → `scripts/sync_lore.sh` automates lore → config copy |
| Tests | Active | Backend and frontend test suites exist; TypeScript build passes |
| Presentation layer | In progress | Ongoing full-English cleanup and portfolio packaging |

---

## Backend

### Core Modules

| Module | Responsibility |
| --- | --- |
| `backend/src/main.py` | HTTP and WebSocket transport, session orchestration, startup wiring |
| `backend/src/game_master.py` | GM response handling, structured parsing, progression, event generation, tension routing |
| `backend/src/state_manager.py` | SQLite persistence, world/player state updates, atomic writes |
| `backend/src/migration_runner.py` | Applies versioned SQL migration files; tracks state in `schema_migrations` table |
| `backend/src/models.py` | Shared domain models, enums, WSMessageType (complete), request/response contracts |
| `backend/src/ws_contracts.py` | Pydantic schemas for all outgoing WS message types |
| `backend/src/context_builder.py` | Multi-layer context assembly; tension-aware L1/L2; episodes + rumors per player |
| `backend/src/vector_store.py` | Lore retrieval and semantic lookup |
| `backend/src/auth.py` | Authentication, invite flow, token lifecycle |
| `backend/src/billing_router.py` | Model selection and BYOK fallback routing |
| `backend/src/memory_manager.py` | Memory extraction, episodic event recording, narrative continuity support |
| `backend/src/behavior_trajectory.py` | Derives dominant behavioral pattern for trajectory-based class mutations |
| `backend/src/reputation_gates.py` | Evaluates faction reputation thresholds; fires gate events on threshold crossing |
| `backend/src/rumor_manager.py` | Faction-biased rumor selection and per-player delivery tracking |
| `backend/src/summarizer.py` | History compression for prompt efficiency |

### Schema Migrations

Versioned SQL files in `backend/migrations/`:

| Migration | Description |
| --- | --- |
| `001_initial_schema.sql` | Full baseline schema (all 14 tables) |
| `002_player_resource_pools.sql` | MP, Stamina, convocation_sent columns |
| `003_conditions_buff_flag.sql` | `is_buff` column on conditions |
| `004_player_economy.sql` | Currency wallet, inventory weight |
| `005_player_macros_spells.sql` | Macros, spell aliases |
| `006_player_backstory_languages.sql` | Backstory change flag, languages |
| `007_player_episodes.sql` | Episodic memory table with importance scoring |

### Backend Config Files

| File | Purpose |
| --- | --- |
| `backend/config/campaign.yaml` | Campaign settings, model selection, game mechanics |
| `backend/config/world.md` | Operational lore copy (sync from `lore/world.md`) |
| `backend/config/world_kernel.md` | Compact L0 world summary (~200 tokens) |
| `backend/config/bestiary_t{1-5}.md` | Creature data by tier for ChromaDB ingestion |
| `backend/config/reputation_gates.yaml` | Faction reputation thresholds → content unlocks |
| `backend/config/rumors.yaml` | Base rumors with per-faction variant text |
| `backend/config/items.yaml` | Item definitions |
| `backend/config/travel.yaml` | Route and terrain data |

### Backend Notes

- The architecture follows a transport-to-domain split, even where legacy modules still coexist with newer layering.
- SQLite with WAL remains the correct choice for the current single-instance deployment model.
- Tension level now drives: LLM model selection, L1 narrative directive, L2 faction world-state signal, and travel encounter probability.
- Episodic memories (`player_episodes`) feed both the GM's context (recent significant events) and the mutation system (behavioral pattern analysis).

---

## Frontend

### Major User Flows

- Authentication and invite redemption
- Character creation with faction and backstory input
- Real-time game session with streamed narrative updates
- Combat event presentation and dice UI
- Character sheet inspection
- Travel visualization
- Optional BYOK configuration
- Ambient and event-driven audio controls
- GM admin dashboard (`/admin`) — player status, campaign controls, invite generation

### New Frontend Additions (March 2026)

| File | Purpose |
| --- | --- |
| `frontend/src/pages/AdminPage.tsx` | GM admin dashboard page |
| `frontend/src/types/wsContracts.ts` | Zod schemas for all WS message types |

### Frontend Notes

- `zod` added as a dependency for WS contract validation. Run `npm install` to apply.
- `parseWSMessage()` and `safeParseWSMessage()` exported from `wsContracts.ts` for use in WS handlers.
- The admin dashboard uses `X-Admin-Secret` header; no JWT required.
- TypeScript compilation passes with `npx.cmd tsc -b`.

---

## Data And Content

The project maintains a split between authored lore and runtime-facing config. The `make sync-lore` target (`scripts/sync_lore.sh`) automates the sync and ChromaDB cache invalidation.

Current content categories:

- world canon
- campaign configuration
- item definitions
- travel data (routes, terrain, encounter tables)
- bestiary data (by tier)
- NPC and class references
- audio prompt packs
- reputation gates (new)
- faction rumors (new)

---

## Testing

### Verified Recently

- `frontend`: TypeScript project build passes via `npx.cmd tsc -b`

### Testing Caveats

- Some environment-level commands remain sensitive to the local shell setup on Windows.
- Vite production build previously hit a local `spawn EPERM` issue while loading config, which appears environment-related rather than a direct code regression.
- After running `npm install` to add `zod`, a full TypeScript validation pass is recommended.

---

## Known Remaining Work

### Content Cleanup

- Normalize travel data descriptions and comments
- Standardize tiered bestiary files
- Rewrite any mixed-language prompt packs

### Repository Readiness

- Choose a stronger public repository name
- Finish README positioning for international recruiters
- Organize commit history using conventional commit categories
- Initialize or connect the GitHub repository
- Push a clean portfolio-ready version

### Optional Product Polish

- Add screenshots or short GIFs to the README
- Add deployment notes and architecture diagrams
- Add a clearer feature matrix for portfolio readers
- Add a short "Why this project matters" section

---

## Readiness Assessment

From an engineering perspective, the project demonstrates:

- real-time full-stack architecture
- game-state orchestration with AI integration
- async backend design with layered context engineering
- typed frontend state management
- configurable lore and world systems
- versioned schema evolution
- tension-driven narrative mechanics
- behavioral mutation tracking
- asymmetric faction information systems
- WebSocket contract validation (Pydantic + Zod)

The remaining work is concentrated in content normalization, repository presentation, and release polish.

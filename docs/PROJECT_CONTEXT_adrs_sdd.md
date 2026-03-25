# Aerus RPG - ADRs And Software Design Summary

> High-level architectural decisions and software design notes for the Aerus platform.

---

## ADR-001: Python And FastAPI For The Backend

**Status:** Accepted

The backend is primarily I/O-bound and centered on orchestration, WebSocket communication, persistence, and AI service integration. Python and FastAPI provide the fastest path for iteration, async support, and ecosystem compatibility with LLM tooling.

---

## ADR-002: SQLite WAL For The Current Persistence Layer

**Status:** Accepted

SQLite with WAL mode is sufficient for the current single-instance runtime. It keeps deployment simple while still supporting concurrent reads and predictable local development.

Constraint:

- Do not scale to multiple write-capable instances without re-evaluating the database strategy.

---

## ADR-003: Four-Layer Context Assembly

**Status:** Accepted

The narrative context is assembled from layered sources:

- static world kernel
- active campaign configuration
- live world and player state
- recent history and compressed memory

This keeps prompts compact enough to be efficient while preserving the most important narrative signals.

---

## ADR-004: React SPA As The Frontend Client

**Status:** Accepted

The frontend is a single-page application optimized for fast interaction, real-time updates, and a compact game-session interface. React + TypeScript supports that well and gives the project a strong portfolio signal for modern frontend work.

---

## ADR-005: WebSocket-First Session Flow

**Status:** Accepted

The game session is event-driven. Narrative output, state updates, dice events, and other live signals should reach connected clients through WebSockets rather than page refresh patterns or polling.

---

## ADR-006: Hybrid Model Strategy

**Status:** Accepted

The project supports both hosted and local AI runtime paths:

- hosted models for primary narrative generation
- local models for summarization or memory support when appropriate
- BYOK support for distributed usage cost

This reduces operating cost while preserving flexibility.

---

## ADR-007: Canonical Lore Plus Runtime Copies

**Status:** Accepted

The project keeps authored lore and backend runtime config in parallel files. This improves authoring clarity, but it requires disciplined synchronization. Whenever canonical content changes, the runtime-facing copy must be updated as part of the same work.

---

## ADR-008: Strict Module Responsibility

**Status:** Accepted

Important boundaries:

- transport stays in `main.py`
- persistence stays in `state_manager.py`
- retrieval stays in `vector_store.py`
- gameplay orchestration stays in `game_master.py`

These boundaries reduce coupling and make the codebase easier to reason about.

---

## Software Design Summary

### Backend Shape

The backend is evolving toward a clearer layered structure while preserving compatibility with legacy modules. The long-term direction is:

- transport layer
- application orchestration
- domain models and rules
- infrastructure adapters

### Frontend Shape

The frontend is organized around domain-focused pages and reusable game UI components. The most important design quality is responsiveness during live play rather than a large multi-page information architecture.

### Content System Shape

The content system is configuration-heavy by design:

- YAML for structured game data
- Markdown for authored lore and design references
- typed frontend and backend contracts for runtime use

This makes the project unusually strong as a portfolio piece because it shows both product implementation and content-system thinking.

---

---

## ADR-009: Versioned Schema Migrations

**Status:** Accepted (March 2026)

Schema evolution is tracked as numbered SQL files in `backend/migrations/`. The `migration_runner.py` module applies pending migrations in order at startup using a `schema_migrations` tracking table.

Rationale: the previous inline migration approach (ALTER TABLE list in `init_db`) was not auditable or reversible. Numbered files provide a git-trackable history of schema changes and a clear upgrade path.

---

## ADR-010: Tension As World State, Not Only Model Selector

**Status:** Accepted (March 2026)

Tension level now affects:
1. LLM model selection (existing behavior)
2. L1 narrative directive injected into the GM prompt (tone guidance per tension band)
3. L2 world state signal (faction aggression, surveillance, crisis posture)
4. Travel encounter probability modifier (existing)

Rationale: a system that claims to have tension as a core mechanic should reflect it in more than just which API endpoint is called.

---

## ADR-011: Episodic Memory As Structured Player History

**Status:** Accepted (March 2026)

Significant player events are stored in `player_episodes` (typed, importance-scored) separate from the character memory blob. This enables:
- Personalized GM context (recent high-importance episodes injected per player)
- Behavioral pattern analysis for class mutations (B5)
- Future: session replay and event auditing

---

## ADR-012: Reputation Gates As Config-Driven Content Routing

**Status:** Accepted (March 2026)

Faction reputation unlocks are defined in `backend/config/reputation_gates.yaml` rather than hardcoded. Each gate fires exactly once per player via quest_flags. The GM receives a `gm_hint` field to contextualize the unlock narratively.

Rationale: content routing should be data-driven and extensible without code changes.

---

## ADR-013: Asymmetric Rumor Delivery

**Status:** Accepted (March 2026)

Rumors are defined with base facts and per-faction variant text in `backend/config/rumors.yaml`. Each player receives the biased version matching their faction. Delivery is tracked per player to avoid repetition.

Rationale: in a cooperative RPG with faction loyalty mechanics, information asymmetry between players creates genuine social dynamics.

---

## ADR-014: WebSocket Contract Schemas On Both Ends

**Status:** Accepted (March 2026)

Backend: `ws_contracts.py` with Pydantic typed models for every outgoing WS message.
Frontend: `wsContracts.ts` with Zod discriminated union schemas mirroring the backend.

Any new WS event type must be added to both files simultaneously.

Rationale: WS message shape mismatches are silent failures in production. Typed contracts at both ends catch these at development time.

---

## Open Design Pressure

The main pressure points are no longer foundational architecture. They are:

- content normalization (travel data, bestiary, prompt packs)
- repository presentation
- release packaging

The architecture now has a credible core with documented decisions, versioned evolution, and behavioral mechanics that reflect the game design intent.

---

## Software Design Summary

### Backend Shape

The backend is evolving toward a clearer layered structure while preserving compatibility with legacy modules. The long-term direction is:

- transport layer
- application orchestration
- domain models and rules
- infrastructure adapters

### Frontend Shape

The frontend is organized around domain-focused pages and reusable game UI components. The most important design quality is responsiveness during live play. The admin dashboard at `/admin` covers GM operational needs without a dedicated backend admin tool.

### Content System Shape

The content system is configuration-heavy by design:

- YAML for structured game data (campaign, items, travel, reputation gates, rumors)
- Markdown for authored lore and design references
- Versioned SQL for schema evolution
- Typed contracts (Pydantic + Zod) for WS protocol

This makes the project unusually strong as a portfolio piece because it shows both product implementation and content-system thinking.

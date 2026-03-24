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

## Open Design Pressure

The main pressure points are no longer foundational architecture. They are:

- content consistency
- English standardization
- repository presentation
- release packaging

That is a good sign. It means the project already has a credible core.

# Aerus RPG - Rules, Engineering Constraints, And Roadmap

> Operational rules for contributors, architecture constraints, and the current roadmap for turning Aerus into a polished international portfolio project.

---

## Engineering Rules

These rules exist to preserve consistency and avoid architectural drift.

### Absolute Rules

1. Use type hints in all Python functions.
2. Prefer structured models and dataclasses over raw dictionaries across module boundaries.
3. Keep SQL access inside `backend/src/state_manager.py`.
4. Keep vector database integration inside `backend/src/vector_store.py`.
5. Load secrets through environment variables only.
6. Wrap SQLite writes in atomic transactions.
7. Use proper logging instead of `print()`.
8. Keep `backend/src/main.py` focused on transport concerns.
9. Route external LLM gameplay calls through `backend/src/game_master.py`.
10. Treat canonical world content as immutable during runtime.
11. Do not scale beyond one machine without rethinking the persistence layer.

---

## Architectural Constraints

### Current Stack Direction

- Backend: Python, FastAPI, WebSocket-first session flow
- Frontend: React + TypeScript SPA
- Database: SQLite WAL
- Retrieval: ChromaDB
- Local AI support: Ollama
- Hosted AI support: OpenRouter-compatible models

### Why These Constraints Exist

- The project is dominated by I/O, orchestration, and narrative state management.
- Development speed matters more than raw throughput at this stage.
- The stack favors experimentation, content iteration, and local-first workflows.

---

## Content Rules

- Public-facing text should be in English.
- Runtime identifiers should remain stable once normalized.
- Canonical lore and runtime copies must stay aligned.
- If a file is renamed, all references must be updated in the same pass.
- Documentation should optimize for recruiter readability, not only author convenience.

---

## Documentation Set

The current core documentation set is:

- `README.md`
- `docs/PROJECT_CONTEXT_overview_stack.md`
- `docs/PROJECT_CONTEXT_architecture_ard.md`
- `docs/PROJECT_CONTEXT_adrs_sdd.md`
- `docs/PROJECT_CONTEXT_rules_roadmap.md`
- `docs/IMPLEMENTATION.md`
- `docs/FRONTEND_SPEC.md`
- `docs/aerus_gm_guide.md`

Supporting world and content references:

- `lore/world.md`
- `lore/bestiary.md`
- `backend/config/world.md`
- `backend/config/campaign.yaml`
- `backend/config/items.yaml`
- `backend/config/travel.yaml`

---

## Short-Term Roadmap

### Phase 1 - English Standardization

- Translate remaining docs, lore packs, prompts, and config comments
- Normalize file names where Portuguese names still remain
- Update all references after file renames
- Run validation scans to catch mixed-language leftovers

### Phase 2 - Repository Professionalization

- Choose a stronger repository name
- refine README positioning for portfolio and hiring use
- add architecture summary and showcase assets
- organize commit history with conventional commit categories

### Phase 3 - GitHub Publication

- initialize or connect the repository
- prepare a clean branch state
- create grouped commits by concern
- push to GitHub with a professional public presentation

---

## Portfolio Positioning

Aerus should be presented as:

`AI-driven multiplayer narrative RPG platform with a real-time full-stack architecture`

Core differentiators:

- AI-assisted Game Master loop
- stateful multiplayer narrative progression
- configurable lore and campaign systems
- WebSocket-driven event streaming
- local-first plus hosted-model runtime strategy

---

## Completion Criteria

The current cleanup phase is complete when:

- all visible project text is in English
- mixed-language identifiers are removed or intentionally preserved as lore-specific names
- README and docs form a coherent international-facing package
- references stay valid after renames
- the codebase passes at least the existing TypeScript validation and spot checks

---

## Next Milestone

Finish the remaining translation hotspots in lore, prompts, bestiary tiers, and travel data. After that, move directly into repository naming, commit organization, and GitHub publishing.

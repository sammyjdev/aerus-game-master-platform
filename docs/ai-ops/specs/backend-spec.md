# Backend Spec (Operational)

Primary references:

- `docs/PROJECT_CONTEXT_architecture_ard.md`
- `docs/PROJECT_CONTEXT_adrs_sdd.md`
- `docs/IMPLEMENTATION.md`

## Core behavior

1. Transport layer remains thin in `backend/src/main.py`.
2. Turn orchestration remains in `backend/src/game_master.py`.
3. SQL persistence remains in `backend/src/state_manager.py`.
4. Retrieval remains in `backend/src/vector_store.py`.

## Verification criteria

- Unit tests pass for modified modules.
- No SQL introduced outside `backend/src/state_manager.py`.
- No vector operations introduced outside `backend/src/vector_store.py`.
- New HTTP/WS fields are reflected in typed contracts.

## Required checks

- `cd backend && .venv/Scripts/python -m pytest tests/ -v`
- Contract parity check with `frontend/src/types/wsContracts.ts`

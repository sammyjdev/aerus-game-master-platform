# Frontend Spec (Operational)

Primary references:
- `docs/FRONTEND_SPEC.md`
- `docs/IMPLEMENTATION.md`

## Core behavior

1. Zustand store is the single source of truth.
2. WebSocket event handling must be schema-validated.
3. Player state rendering reflects backend deltas without ad hoc state forks.

## Verification criteria

- `cd frontend && npm test`
- `cd frontend && npm run build`
- WS event additions/removals are mirrored in Zod schema.

## Required checks

- Type-safe event parsing path in `frontend/src/hooks/useWebSocket.ts`.
- Contract sync with backend `backend/src/ws_contracts.py`.

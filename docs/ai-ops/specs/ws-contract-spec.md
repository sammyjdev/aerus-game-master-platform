# WS Contract Spec

Canonical backend contract:

- `backend/src/ws_contracts.py`

Canonical frontend mirror:

- `frontend/src/types/wsContracts.ts`

## Required parity rules

1. Every outbound WS message from backend has a corresponding Zod schema.
2. Any added required field in backend contract must be required in frontend schema.
3. Any message removed from backend must be removed or deprecated in frontend parser.

## Verification criteria

- Contract review diff references both files.
- Runtime parsing in frontend uses safe parser path.
- Backend send path validates or logs schema violations.

# Aerus Game Master Platform Frontend

Frontend for Aerus Game Master Platform built with React, TypeScript, and Vite.

## Stack

- React 19
- TypeScript 5
- Vite 8
- Zustand
- React Router
- Howler
- Vitest + Testing Library

The main interface animations were migrated to CSS `@keyframes`, reducing runtime overhead during narrative streaming.

## Covered flows

- login and first access via invite;
- character creation;
- main game loop over WebSocket;
- isekai intro and secret objective;
- initial cooperative mission;
- sheet with macros and spell aliases;
- audio panel;
- BYOK panel;
- debug snapshot and travel components.

## Scripts

```bash
npm install
npm run dev
npm run build
npm run lint
npm run test
npm run test:watch
```

## Local environment

Create `frontend/.env.local` from `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEBUG_MODE=false
```

The backend must be running to validate the full flow.

## Tests

The manual validation guide lives in [TESTING.md](TESTING.md).

Quick summary:

1. `npm run test`
2. `npm run build`
3. validate login, character creation, gameplay, cooperative mission, BYOK, audio, and WS events against the local backend
4. run the E2E tests from `backend/e2e/`

## Notes

- Frontend contracts assume compatibility with the current backend under `backend/src/`.
- BYOK usage policy is enforced on the backend.

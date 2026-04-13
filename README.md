# Aerus Game Master Platform

Monorepo for an AI-driven dark fantasy multiplayer narrative RPG platform, with a FastAPI backend, a React frontend, and an LLM-powered Game Master responsible for turns, narrative flow, and persistent campaign state.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111827)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active%20Development-22c55e)

## Overview

The project combines:

- an async backend with FastAPI, SQLite, and ChromaDB;
- a React + TypeScript + Vite SPA frontend;
- WebSocket-based real-time updates;
- canonical lore separated from runtime data;
- local-first execution with Ollama and BYOK/OpenRouter support.

The main flow already covers invite-based authentication, character creation, isekai intro, the core gameplay loop with streaming narrative, the initial cooperative mission, macros, aliases, debug tools, audio, and basic travel tracking.

## Repository structure

```text
.
├── backend/    # API, WebSocket, persistence, rules, and tests
├── frontend/   # React SPA, client state, and game UI
├── docs/       # technical, functional, and product documentation
├── lore/       # canonical world, bestiary, and authored content
├── Makefile    # local development helper commands
└── README.md
```

## Architecture

### Backend

- `backend/src/main.py`: HTTP/WebSocket transport layer and application lifecycle.
- `backend/src/game_master.py`: turn orchestration, narrative processing, and event dispatch.
- `backend/src/state_manager.py`: SQLite access and state persistence.
- `backend/src/vector_store.py`: lore ingestion and semantic retrieval through ChromaDB.
- `backend/src/application/` and `backend/src/infrastructure/`: incremental adoption of a layered architecture.

### Frontend

- `frontend/src/pages/`: main application pages.
- `frontend/src/components/`: domain-focused UI (`character`, `combat`, `travel`, `ui`).
- `frontend/src/hooks/`: WebSocket, audio, and session integrations.
- `frontend/src/store/`: global game state with Zustand.
- `frontend/src/api/`: HTTP client layer.

### Lore and runtime

- `lore/` is the canonical source of truth.
- `backend/config/` is the operational copy used by runtime services.

## AI documentation operations

For task-oriented AI workflows (Specs, Rules, Agent playbooks, Skills, Harness, and non-destructive migration controls), start from:

- `docs/ai-ops/README.md`

## Requirements

- Python 3.11+
- Node.js 20+
- `npm`
- Ollama locally if you want to run the local-first mode

## Local setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install chromadb --prefer-binary
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill at least these variables in `backend/.env`:

- `FERNET_KEY`
- `JWT_SECRET`
- `PASSWORD_SALT`
- `AERUS_LOCAL_ONLY`
- `AERUS_OLLAMA_URL`
- `AERUS_OLLAMA_GM_MODEL`
- `AERUS_OLLAMA_SUMMARIZER_MODEL`
- `OPENROUTER_API_KEY` if you want external provider support or admin fallback

Recommended profiles:

- Local development on a 12 GB GPU:
  - `AERUS_LOCAL_ONLY=true`
  - `AERUS_OLLAMA_GM_MODEL=qwen2.5:7b-instruct`
  - `AERUS_OLLAMA_EXTRACTOR_MODEL=qwen2.5:7b-instruct`
  - `AERUS_OLLAMA_SUMMARIZER_MODEL=phi4:mini`
  - This favors full-GPU iteration speed over the higher quality ceiling of larger local models.

- OpenRouter-first validation or production:
  - `AERUS_LOCAL_ONLY=false`
  - `OPENROUTER_API_KEY=...`
  - keep Ollama configured only as a local fallback
  - hosted model routing is selected by tension in `backend/src/billing_router.py`

Quick key generation:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

Expected defaults:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEBUG_MODE=false
```

## Running the project

### Backend

```powershell
cd backend
.venv\Scripts\python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
```

### Frontend

```powershell
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### Makefile option

From the project root:

```powershell
make setup
make frontend-install
make dev
make frontend
```

## Basic usage flow

1. Start backend and frontend.
2. Generate an invite with `POST /admin/invite` or `make invite`.
3. Open the UI, create an account, and create a character.
4. Enter the game and follow the isekai intro.
5. Interact through the main WebSocket-driven experience.

## Useful commands

### Backend tests

```powershell
cd backend
.venv\Scripts\python -m pytest tests -v
```

### Frontend tests

```powershell
cd frontend
npm run test
```

### Frontend build

```powershell
cd frontend
npm run build
```

### Playwright E2E

```powershell
cd backend
.venv\Scripts\pip install -r requirements-e2e.txt
.venv\Scripts\python -m pytest e2e/test_app_e2e_playwright.py -v -s
```

### GM evaluation workflow

Use `backend/eval/gm_eval.py` as a layered evaluation suite instead of a single monolithic run.

Recommended operating flow:

- Daily GM/runtime changes:

  ```powershell
  cd backend
  $env:AERUS_EVAL_PROFILE="default"
  .venv\Scripts\python eval/gm_eval.py
  ```

  This runs the fast `critical path` subset of the core tier: onboarding, combat, reputation, coop gating, healing, multiplayer delta behavior, missing inventory handling, and lore grounding.

- Full core regression gate:

  ```powershell
  cd backend
  $env:AERUS_EVAL_PROFILE="core-full"
  .venv\Scripts\python eval/gm_eval.py
  ```

  This runs the entire `core` tier when you want broader contract and progression coverage.

- Behavior expansion or narrative tuning:

  ```powershell
  cd backend
  $env:AERUS_EVAL_PROFILE="extended"
  .venv\Scripts\python eval/gm_eval.py
  ```

  This focuses on richer edge cases, lore pressure, disputes, morally heavy actions, and other extended behavior scenarios.

- Full manual baseline:
  ```powershell
  cd backend
  $env:AERUS_EVAL_PROFILE="full-baseline"
  .venv\Scripts\python eval/gm_eval.py
  ```
  This runs all tiers and replays even the scenarios that were already green.

Useful overrides:

- `AERUS_EVAL_TIER=core|extended|all`
- `AERUS_EVAL_INCLUDE_STABLE=1`
- `AERUS_EVAL_SCENARIOS=1,4,7`
- `AERUS_EVAL_LIMIT=5`
- `AERUS_EVAL_MAX_TOKENS=900`
- `AERUS_EVAL_SCENARIO_TIMEOUT_SECONDS=75`

Recommended evaluation strategy by provider:

- Local/Ollama iteration:
  - use the `default` profile for prompt/runtime changes
  - use `core-full` before merges that affect contracts, progression, or multiplayer state handling
  - prefer smaller local models for faster feedback loops
- OpenRouter quality validation:
  - use `extended` before important merges
  - use `full-baseline` when changing prompts, contracts, or model-routing behavior

Report interpretation:

- `Contract checks`: output shape, IDs, multiplayer deltas, and retrieval-friendly structured fields.
- `Narrative checks`: tone, lore, consequences, dramatic weight, and behavioral quality.
- `Core tier`: regression gate for routine work.
- `Extended tier`: deeper review before major merges or model/prompt changes.

## Git-ready checklist

Before pushing the repository:

- keep `backend/.env` local only; use `backend/.env.example` as the committed template
- do not commit local databases such as `*.db`, `*.db-wal`, or `*.db-shm`
- do not commit Chroma runtime folders such as `backend/chroma_db/` or root `chroma_db/`
- do not commit evaluation history or temporary logs from `backend/eval/history/` and `backend/eval/*.log`
- prefer committed config changes in `backend/config/campaign.yaml`, but keep API keys only in environment variables
- run backend tests and at least one `GM_EVAL` profile before opening a PR

Suggested pre-push review:

```powershell
git status --short
git diff --stat
```

If you are preparing a hosted-model branch, verify these env assumptions locally and do not hardcode them in tracked files:

- `AERUS_LOCAL_ONLY=false`
- `OPENROUTER_API_KEY` set in your shell or `.env`
- Ollama values kept only as optional fallback

## Lore synchronization

When you change canonical files inside `lore/`, sync the operational copies:

```powershell
Copy-Item lore\world.md backend\config\world.md -Force
Copy-Item lore\bestiary.md backend\config\bestiary.md -Force
```

## Related documentation

- `docs/IMPLEMENTATION.md`: current implementation status and coverage.
- `docs/FRONTEND_SPEC.md`: expected frontend behavior.
- `docs/PROJECT_CONTEXT_overview_stack.md`: overview, stack, and infrastructure.
- `docs/PROJECT_CONTEXT_architecture_ard.md`: architecture and requirements.
- `docs/PROJECT_CONTEXT_adrs_sdd.md`: architectural decisions and design details.
- `docs/PROJECT_CONTEXT_rules_roadmap.md`: project rules, model strategy, and roadmap.
- `docs/aerus_gm_guide.md`: narrative voice and GM guidelines.
- `backend/e2e/README.md`: E2E execution and debugging notes.

## Commit convention

This project should follow Conventional Commits to keep history clean and improve release notes:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` refactor without behavioral change
- `test:` tests
- `chore:` maintenance, tooling, or housekeeping
- `build:` build, dependencies, or packaging
- `ci:` automation and pipelines

Examples:

```text
feat: add travel panel with regional maps
fix: correct silent token refresh over websocket
docs: rewrite README with local setup and architecture
```

## Repository publishing

Before pushing to GitHub:

- confirm that local files such as `backend/.env`, `backend/aerus.db`, `backend/chroma_db/`, `frontend/.env.local`, `node_modules/`, and `dist/` will not be versioned;
- review the main documentation;
- organize commits by type;
- choose a professional repository name that fits the product.

Selected repository name:

- `aerus-game-master-platform`

## Troubleshooting

### Frontend does not connect

- confirm backend is running at `http://localhost:8000`;
- confirm frontend is running at `http://localhost:5173`;
- review `VITE_API_URL` and `VITE_WS_URL`.

### Authentication or session issues

- verify `JWT_SECRET` is configured on the backend;
- clear browser `localStorage` and try again.

### Runtime lore is outdated

- sync `lore/` back into `backend/config/`.

### Residual state in tests

- remove `backend/aerus.db` and `backend/chroma_db/` before sensitive scenarios.

## License

Define before making the repository public on GitHub.

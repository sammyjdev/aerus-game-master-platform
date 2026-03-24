# E2E (Playwright + Python)

End-to-end automation for the full application through the web interface, based on the checklist in `frontend/TESTING.md`.

## Prerequisites

- Backend running at `http://localhost:8000`
- Frontend running at `http://localhost:5173`
- Backend Python virtual environment available (`backend/.venv`)

## Installation

From the `backend/` directory:

```bash
.venv/Scripts/pip install -r requirements-e2e.txt
.venv/Scripts/python -m playwright install chromium
```

## Run

```bash
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v
```

## Optional variables

- `E2E_FRONTEND_URL` (default: `http://localhost:5173`)
- `E2E_BACKEND_URL` (default: `http://localhost:8000`)
- `E2E_HEADLESS` (default: `true`)
- `E2E_SLOW_MO_MS` (default: `0`)
- `E2E_TIMEOUT_MS` (default: `90000`)
- `E2E_ADMIN_SECRET` (if `/admin/invite` is protected)

Example (PowerShell):

```powershell
$env:E2E_HEADLESS="false"
$env:E2E_SLOW_MO_MS="200"
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v
```

## Current coverage

- `test_full_e2e_flow_via_frontend`
  - first access with invite via UI
  - character creation via UI
  - entry into `/game` and main shell
  - volume panel visibility and controls
  - BYOK panel local validation
  - debug panel and snapshot consistency between backend and frontend
  - macro creation and use in `ActionInput`
  - reload and a new snapshot validation
- `test_multiplayer_cooperative_mission_flow`
  - two players in independent sessions
  - cooperative mission section validation in the character sheet
  - parallel actions and cooperative flag verification via `/debug/state`
- `test_scaling_preview_increases_from_solo_to_group`
  - compares debug snapshot in solo vs group context
  - validates increase in `alive_players`, `encounter_scale_preview`, and `boss_scale_steps_preview`

## Run a specific scenario

```bash
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -k multiplayer_cooperative_mission_flow -v -s
```

## Notes

- Rare events such as death/spectator mode, class mutation, or secret objective hints at specific thresholds still benefit from complementary manual validation over longer scenarios.

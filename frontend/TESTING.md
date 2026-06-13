# Aerus Game Master Platform End-to-End Manual Validation Guide

Manual guide for validating the full Aerus Game Master Platform experience through the web interface.

The goal here is not to test isolated frontend components. The goal is to confirm that:

1. The interface sends the correct data.
2. The backend accepts, persists, and processes that data.
3. The frontend reflects the real backend response without inconsistencies.
4. The complete flow stays stable across login, creation, gameplay, streaming, persistence, and reconnection.

> UI labels quoted below assume the English locale. If you run the app in Portuguese,
> the corresponding `pt.json` labels will appear instead.

## 1. Prerequisites

Before opening the browser, confirm:

1. Backend running at `http://localhost:8000`.
2. Frontend running at `http://localhost:5173`.
3. Backend configured for local-first validation (`AERUS_LOCAL_ONLY=true`).
4. At least one invite code available.
5. If you want to validate BYOK, have a test OpenRouter key on hand.

## 2. Bringing up the environment

### Backend

In the `backend/` directory:

```bash
.venv/Scripts/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
```

### Frontend

In the `frontend/` directory:

```bash
npm install
npm run dev
```

## 3. Preparing test data

### Generate an invite code

On the backend, use one of these paths:

```bash
curl -X POST http://localhost:8000/admin/invite
```

or the project's existing task.

### Suggested users

Use simple names to make visual inspection easier:

- `kael_test`
- `lyra_test`
- `nox_test`

## 4. Validation scope

Each scenario below should be read as an E2E test via the interface.

At every step, always validate three things:

1. What the UI does immediately.
2. What that proves about the backend.
3. What comes back to the UI after processing.

## 5. E2E checklist via the interface

## 5.1 Login and first access

### Scenario A — first access with invite

1. Open the root route `/`.
2. Confirm that the active tab is `First access`.
3. Fill in `Invite code`, `Username`, and `Password`.
4. Click `Enter the world`.

**Expected in the interface:**

- No visual error.
- Redirect to `/character`.
- Token saved and session active.

**What this validates on the backend:**

- The invite was accepted and consumed correctly.
- The user was created successfully.
- The returned JWT token is valid.
- The frontend was able to use the real API response without an artificial fallback.

### Scenario B — existing account login

1. Go back to `/`.
2. Switch to the `I already have an account` tab.
3. Fill in the `Username` and `Password` already created.
4. Click `Enter`.

**Expected in the interface:**

- If the character already exists, go to `/game`.
- If the character does not exist yet, go to `/character`.

**What this validates on the backend:**

- Authentication works for an already-persisted account.
- The backend can distinguish an account with a created character from one without.
- The frontend is correctly interpreting the state returned by the API.

### Scenario C — invalid credentials

1. Enter the wrong password.
2. Submit the form.

**Expected in the interface:**

- Visible error message.
- No redirect.

**What this validates on the backend:**

- The backend rejects invalid credentials.
- The frontend does not mask an authentication error as success.

## 5.2 Character creation

1. On the `/character` screen, fill in `Name`.
2. Change the `Race` in the select.
3. Click at least two factions and observe the visual change.
4. Fill in `Backstory` with fewer than 50 characters.

**Expected in the interface:**

- Submit button disabled.

**What this validates in the full flow:**

- The frontend is blocking invalid submission before calling the API.
- The form avoids bad requests to the backend.

5. Complete `Backstory` with at least 50 characters.
6. Click `Enter the world`.

**Expected in the interface:**

- Request completes without error.
- Redirect to `/game`.
- The backend infers the class using a local model with a deterministic fallback.

**What this validates on the backend:**

- The character was persisted with name, race, factions, and backstory.
- Class inference ran on the backend.
- The character's initial state is consistent enough to open the game.

## 5.3 Isekai intro

On the character's first entry into the game:

1. Wait for the summoning event.
2. Read the intro narrative.
3. Confirm that the secret objective appears on screen.
4. Click to enter the game.

**Expected in the interface:**

- The intro appears only when it has not yet been completed.
- The secret objective is shown to the player.
- After entering, the main interface is unlocked.

**What this validates on the backend:**

- The backend generated the initial summoning.
- The secret objective was assigned to the character.
- The intro state was persisted so it does not repeat incorrectly.

## 5.4 Loading the main game state

Validate on `/game`:

1. `NarrativePanel` visible.
2. `CharacterSheet` visible.
3. `ActionInput` visible.
4. `EventLog` visible.
5. `ConnectionStatus` visible.
6. `VolumeSettings` button visible.
7. `BYOK` button visible.

**Expected in the interface:**

- No broken main component.
- Responsive layout at normal desktop width.

**What this validates on the backend:**

- The initial game-state load returned enough data to build the screen.
- The character sheet, history, connection, and events came back with a structure compatible with the UI.

## 5.5 Action submission and turn resolution

1. Type a simple action in `ActionInput`.
2. Click `Send`.

**Expected in the interface:**

- Input clears after submission.
- The button is temporarily blocked.
- A `Waiting for other players...` countdown appears.
- When the GM response arrives, the narrative starts filling the history.

**What this validates on the backend:**

- The action left the frontend and reached the backend via WebSocket.
- The backend recorded the player's action.
- The GM processing cycle was triggered.
- The turn result was delivered back to the frontend without breaking the protocol.

### Macro validation

1. Open `CharacterSheet`.
2. Create a simple macro, for example `/strike`.
3. Go back to the input.
4. Type exactly `/strike`.
5. Send.

**Expected in the interface:**

- The frontend expands the macro before sending.

**What this validates in the full flow:**

- Local expansion remains compatible with the payload the backend accepts.
- The backend processes the expanded action normally during the turn.

## 5.6 History, streaming, and response consistency

1. Send 2 or 3 actions in a row, waiting for the responses.
2. Observe the `NarrativePanel` and the history.

**Expected in the interface:**

- Narrative tokens appear progressively.
- At the end of the turn, the stream closes correctly.
- History keeps both player and GM entries.

**What this validates on the backend:**

- The backend is emitting narrative chunks/tokens in the expected format.
- The stream closes without leaving the UI stuck in an intermediate state.
- The persisted history and the displayed history stay consistent across turns.

## 5.7 Event log

During the turns:

1. Open the `EventLog`.
2. Confirm that game events enter the list.

**Expected in the interface:**

- The most recent events appear.
- The log keeps at most the window configured by the frontend/store.

**What this validates on the backend:**

- The backend is emitting structured events during the turn.
- The frontend is consuming the correct events, not just rendering local placeholders.

## 5.8 CharacterSheet and edit persistence

### Backstory

1. Open the sheet area related to backstory.
2. Change the text.
3. Save.

**Expected in the interface:**

- Coherent visual feedback.
- Character state updated without breaking the screen.

**What this validates on the backend:**

- The backend accepted the backstory update.
- The next read of the character reflects the persisted change.

### Spell aliases

1. Open the spells section.
2. Select an existing element.
3. Enter an alias.
4. Save.

**Expected in the interface:**

- The alias appears immediately in the UI.
- Backend persistence working.

**What this validates on the backend:**

- The alias was saved and associated with the correct element.
- A page reload must keep the alias loaded from the API, not only from local state.

### Macros

1. Open the macros section.
2. Create a new macro.
3. Save.

**Expected in the interface:**

- The macro appears immediately.
- It can be used in `ActionInput`.

**What this validates on the backend:**

- The macro was persisted durably.

## 5.9 Mandatory initial cooperative mission

1. Open two sessions (two different users) and enter the game.
2. Confirm on both sheets:
   - Shared location: `Isles of Myr`.
   - `Initial Cooperative Mission` section with status `Active (blocking)`.
   - Initial progress `0/N`.
3. Send an action with player A and validate that progress updates for both.
4. Send an action with player B and validate completion once all living players have participated.

**Expected in the interface:**

- Progress rises in real time via the `COOP_MISSION` event.
- When all living players participate, the status changes to `Completed`.

**What this validates on the backend:**

- Cooperative flags persisted in `quest_flags`.
- A mandatory mission that blocks until collective participation completes.

## 5.10 Balancing by player count

1. Run a turn with 1 player and open `Debug` -> `Snapshot`.
2. Record the `runtime` fields `alive_players`, `encounter_scale_preview`, and `boss_scale_steps_preview`.
3. Connect more players (group table) and repeat the snapshot.
4. Validate that:
   - `alive_players` increased,
   - `encounter_scale_preview` increased,
   - `boss_scale_steps_preview` advanced in steps of 2 players.

**Expected in the interface:**

- Encounters with more players return narrative with greater pressure/tactics.
- The boss keeps its base and only raises difficulty in steps of 2 players.

**What this validates on the backend:**

- The GM prompt receives and applies party-size scaling.
- The special boss curve was injected into the GM's decision contract.

## 6. E2E automation (Playwright Python)

In the `backend/` directory:

```bash
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v -s
```

Current automated coverage:

- `test_full_e2e_flow_via_frontend`
- `test_multiplayer_cooperative_mission_flow`
- `test_scaling_preview_increases_from_solo_to_group`

## 5.9 Volume panel

1. Click the `VolumeSettings` button.
2. Change the `Music`, `Effects`, and `Ambient` sliders.
3. Close and reopen the panel.
4. Reload the page.

**Expected in the interface:**

- Values persist.
- Idle music reacts to the connection/stream state.

**What this validates in the real flow:**

- The frontend is correctly synchronizing audio state and game state.
- Status changes received from the backend affect the expected behavior of the audio layer.

## 5.10 BYOK panel

1. Click the `BYOK` button.
2. Confirm the panel opens.
3. Enter a test OpenRouter key.
4. Click `Save key`.

**Expected in the interface:**

- Visible success message.
- No crash on screen.

**What this validates on the backend:**

- The key-registration API responded successfully.
- The key was accepted by the backend in the expected format.
- The frontend handles real API responses and errors.

### Invalid scenario

1. Open the BYOK panel.
2. Try to save an empty value.

**Expected in the interface:**

- A local error message in the panel itself.

**What this validates in the full flow:**

- The frontend applies basic validation before sending an unnecessary request.

## 5.11 WebSocket reconnection

1. Open the game.
2. Temporarily shut down the backend or drop the network connection.
3. Observe `ConnectionStatus`.
4. Restore the backend/connection.

**Expected in the interface:**

- State changes to `reconnecting`.
- After recovery, it reconnects without reloading the page.
- History and current state stay consistent.

**What this validates on the backend and protocol:**

- The backend accepts the reconnected session again.
- The frontend rebuilds the connection without losing essential state.
- The WebSocket contract stays consistent after a transient failure.

## 5.11.1 Validation via Debug Snapshot (backend vs frontend)

With the game open at `/game`:

1. Open the `Debug` panel in the lower-right corner.
2. Click `Snapshot`.
3. Check the `Backend vs frontend comparison` block.

**Expected in the interface:**

- Snapshot loads without an authentication error.
- Shows backend and frontend data side by side.
- Displays `Local state consistent with backend snapshot` when there is no divergence.

**What this validates on the backend and frontend:**

- The `GET /debug/state` API responds with real persisted-state data.
- Frontend state hydration is consistent with the server state.
- Differences in `turn`, `class`, `hp/mp/stamina`, and `campaign_paused` are detectable without manual database inspection.

### Scenario with forced divergence

1. Send an action and click `Snapshot` immediately during turn processing.
2. Repeat the snapshot after `stream_end`.

**Expected in the interface:**

- There may be a transient divergence during processing.
- After the turn ends, the diffs should disappear or shrink to expected cases.

## 5.12 Special gameplay events

Some events require backend help or specific turns. Validate them when they occur in the normal game flow.

### DiceRoll

**Expected in the interface:**

- A dice overlay/animation appears.
- Critical/fumble are indicated correctly.

**What this validates on the backend:**

- The backend is emitting a roll event with a coherent payload.
- The frontend correctly interprets success, critical failure, and ordinary failure.

### Class mutation

**Expected in the interface:**

- When the configured level milestone is reached, the class shown on the sheet changes.
- The event appears in the game flow.

**What this validates on the backend:**

- Progression was applied to the persisted state.
- The class mutation was not merely cosmetic; it came from the character's real state.

### Secret objective hints

**Expected in the interface:**

- The frontend receives a `FACTION_CONFLICT` event.
- The hint appears in the flow/event log without directly exposing the full objective.

**What this validates on the backend:**

- The backend is tracking secret-objective progress.
- The hint trigger is being computed and emitted correctly.

### Spectator mode

When the character dies:

**Expected in the interface:**

- `SpectatorOverlay` appears.
- The UI reflects `status: dead`.

**What this validates on the backend:**

- The death state was persisted.
- The frontend is reacting to the character's real state, not a local simulation.

## 5.13 Minimum responsiveness

Validate at reduced width or with responsive DevTools:

1. Open `/game`.
2. Simulate mobile/tablet width.

**Expected in the interface:**

- `layout-grid` collapses to a single column.
- `CombatOrder` disappears on smaller screens.
- `EventLog` and `ConnectionStatus` stop conflicting visually.
- Volume and BYOK buttons remain accessible.

**What this validates in the application flow:**

- The interface stays usable during real gameplay on smaller screens.
- Consuming backend responses stays functional even with a reduced layout.

## 6. Quick E2E smoke-test script

If you want a short validation of the entire application via the interface:

1. Login/redeem.
2. Create a character.
3. Confirm the isekai intro.
4. Enter the game.
5. Send an action.
6. Validate narrative and event log.
7. Create a macro and use it in the input.
8. Save a spell alias.
9. Open `VolumeSettings` and change volumes.
10. Open `BYOK` and save a key.
11. Reload the page and confirm the session is still functional.

## 7. Mandatory confirmations after reload

After running the main scenarios, reload the page at `/game` and confirm:

1. The session stays valid without improperly asking for a new login.
2. The loaded character is the same one created earlier.
3. The edited backstory stays saved.
4. Macros stay saved.
5. Spell aliases stay saved.
6. The secret objective stays consistent with the character.
7. The history and general state did not revert to an incorrect initial state.

If any of these items fails, the problem is not merely visual. It indicates a failure of persistence, synchronization, or rehydration between backend and frontend.

## 8. Support commands

### Automated tests

```bash
npm run test
```

### E2E via Playwright (Python)

In the `backend/` directory:

```bash
.venv/Scripts/pip install -r requirements-e2e.txt
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python -m pytest e2e/test_app_e2e_playwright.py -v
```

### Validation build

```bash
npm run build
```

## 9. Application acceptance criteria via the frontend

The application is considered manually validated by this script when:

1. The `/` -> `/character` -> `/game` flow works without errors and without state inconsistencies.
2. Actions sent through the interface reach the backend, are processed, and return as coherent narrative and events.
3. Sheet edits made in the UI truly persist after reload.
4. Intro, secret objective, hints, rolls, class mutation, and spectator mode appear when the backend triggers them.
5. WebSocket reconnects correctly without corrupting the session or history.
6. BYOK and audio settings work without breaking the main flow.
7. The behavior observed in the interface confirms that frontend and backend respond as a single integrated application.
8. Automated tests and the build keep passing as support, but do not replace this E2E validation.

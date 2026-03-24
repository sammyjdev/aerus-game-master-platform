# Aerus RPG - Frontend Specification

> Reference document for the Aerus frontend application.

---

## Purpose

The frontend delivers the player-facing real-time experience for Aerus: authentication, character creation, narrative play, state inspection, travel visibility, audio cues, and cooperative multiplayer feedback.

---

## Stack

- React 19
- TypeScript
- Vite
- Zustand
- Howler.js
- Custom CSS

The current UI no longer depends on Tailwind as its primary styling layer. Most presentation lives in `src/index.css` and `src/App.css`.

---

## Main Screens

- `LoginPage.tsx`
- `CharacterCreationPage.tsx`
- `GamePage.tsx`
- `IsekaiIntro.tsx`
- `CampfireScreen.tsx`
- `SpectatorOverlay.tsx`

---

## Main Components

### Narrative

- `NarrativePanel.tsx`: streamed narrative output

### Character

- `CharacterSheet.tsx`: stats, inventory, conditions, and key identity data

### Combat

- `DiceRoller.tsx`
- `ManualDiceRoller.tsx`
- `CombatOrder.tsx`

### UI

- `ActionInput.tsx`
- `EventLog.tsx`
- `ConnectionStatus.tsx`
- `VolumeSettings.tsx`
- `ByokSettings.tsx`

### Travel

- `TravelTracker.tsx`
- `MapViewer.tsx`

---

## Core Frontend Responsibilities

- keep the player authenticated
- manage reconnect and token refresh behavior
- render streamed narrative in real time
- reflect server-side deltas in the store
- present combat and event feedback clearly
- support audio cues and ambient playback
- show cooperative mission state and travel progress

---

## Data Flow

### REST

REST is used for:

- invite redemption
- login
- character creation
- profile updates
- BYOK registration
- manual dice flow endpoints

### WebSocket

WebSocket is used for:

- narrative streaming
- dice events
- game events
- state updates
- reconnection sync
- isekai convocation delivery

---

## Store Responsibilities

The Zustand store should remain the single frontend source of truth for:

- player state
- world state
- inventory
- conditions
- event log
- travel state
- connection state
- audio settings

---

## UX Principles

- narrative must remain readable during streaming
- combat feedback must interrupt clearly without feeling chaotic
- character information must be available without leaving the main session
- reconnect behavior must feel resilient and quiet
- cooperative-state visibility should reduce confusion in multiplayer sessions

---

## Accessibility And Interaction

- keyboard-friendly action submission
- visible connection state
- readable event emphasis
- clear loading and thinking states
- sensible focus management on overlays and dialogs

---

## Testing Expectations

The frontend should be validated through:

- TypeScript build checks
- focused component tests
- end-to-end flow coverage for core user journeys

Current important validation:

- `npx.cmd tsc -b`

---

## Portfolio Positioning

The frontend is part of what makes Aerus a strong portfolio project. It demonstrates:

- real-time UI updates
- typed state management
- full-stack multiplayer integration
- AI-assisted narrative presentation
- gameplay-oriented interface design

---

## Maintenance Rule

Keep all visible labels, helper text, docs, and user-facing fallback strings in English.

> Extracted from the project context bundle - overview, stack, and infrastructure.

# Aerus RPG - Project Context Overview

> Updated for the current portfolio-oriented English repository.
> Use this file as a quick project briefing before deeper implementation or design work.

### Implementation Addendum

- Shared onboarding start is fixed to the **Isles of Myr** for every player.
- Secret objectives remain persisted per player and visible in the website beyond the intro sequence.
- An initial **mandatory cooperative mission** exists and blocks progression until all living players take part.
- Encounter scaling and boss scaling are injected into the GM context based on active party size.
- `/debug/state` exposes scale previews to validate encounter logic.
- Playwright E2E coverage includes full flow, multiplayer cooperative mission, and solo-vs-group scaling checks.

---

## Index

1. [Overview](#1-overview)
2. [Stack and Infrastructure](#2-stack-and-infrastructure)

---

## 1. Overview

**Name:** Aerus RPG  
**Type:** Browser-based multiplayer dark fantasy text RPG  
**GM:** AI agent powered by remote LLMs plus local fallback tooling  
**World:** Aerus, 4,217 years after the Sealing Ritual  
**Primary inspirations:** Elden Ring, Dark Souls, Bloodborne  
**Canonical lore sources:** `lore/world.md` and `lore/bestiary.md`, mirrored into `backend/config/` for runtime use

### What It Is

- A narrative RPG where the GM is an LLM grounded by lore, memory, and explicit mechanics.
- Up to 5 players interact in real time through a React SPA over WebSocket.
- Players arrive in Aerus through an **isekai summoning framework** orchestrated by the Dome.
- Each player is tied to a faction with a public agenda and a secret objective.
- Cost is split through a BYOK-aware model: the admin covers shared overhead, while players can cover their own action cost.
- Main narration runs through OpenRouter-capable models, while summarization and memory compression can run locally through Ollama.

### What It Is Not

- Not a generic chatbot.
- Not a massive persistent MMO.
- Not a monetized MVP.

---

## 2. Stack and Infrastructure

### Core Stack

| Component | Technology | Why it exists |
| --- | --- | --- |
| Backend | Python 3.11+ + FastAPI | Async-friendly, practical for orchestration and AI integration |
| WebSocket | Native FastAPI support | Minimal extra infrastructure |
| Frontend | React SPA + TypeScript | Clear UI separation and modern DX |
| Persistence | SQLite + WAL via `aiosqlite` | Simple local-first persistence with no external DB required |
| Vector Store | ChromaDB | Semantic lore and bestiary retrieval |
| LLM Gateway | OpenRouter-compatible APIs | Broad model support and BYOK flexibility |
| Local Model Runtime | Ollama | Free local summarization and structured helper tasks |
| Backend Deploy | Fly.io (GRU) | Low latency for Brazil-based hosting and always-on runtime |
| Frontend Deploy | Vercel | Simple push-to-deploy frontend hosting |
| Config | YAML + Markdown | Editable campaign data without changing code |
| BYOK Crypto | Fernet | Encrypted player-owned API keys at rest |

### Critical Infra Decisions

**SQLite in WAL mode**

```python
await db.execute("PRAGMA journal_mode=WAL;")
await db.execute("PRAGMA synchronous=NORMAL;")
```

**Single-machine backend assumption**

```toml
[env]
  PRIMARY_REGION = "gru"

min_machines_running = 1
max_machines = 1
```

The backend should remain single-instance until the persistence layer is redesigned around a networked database.

**Long-lived JWT with silent refresh**

- Tokens last for months rather than minutes.
- On validated activity, the backend can emit a refresh event if the token is approaching expiry.
- The frontend updates the stored token silently.

**Action batching**

```python
ACTION_WINDOW_SECONDS = 3.0
```

After the first action in a turn batch, the system waits briefly for additional party actions so the GM can narrate a single combined response.

**Resilience expectations**

- LLM timeout target: 15 seconds
- Fallback `gm_thinking` event when narration is delayed
- Automatic reconnect with full state sync on client recovery

### Local Admin Hardware Notes

Validated local setup assumptions:

- **CPU:** Ryzen 7 5800X3D class
- **RAM:** 32 GB
- **GPU:** RTX 4070 Ti / 12 GB VRAM class
- **OS:** Windows 11

Validated local models include `qwen2.5:14b-instruct` for structured outputs and `phi4:14b` for supporting narrative or summarization tasks.

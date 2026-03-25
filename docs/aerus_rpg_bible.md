# AERUS RPG - Project Bible

> Version: 4.1 - Updated index with accurate line counts and travel document (2026-03-25)
> This bible is split into smaller themed documents for easier navigation, maintenance, and model consumption.
> Always edit the corresponding themed document, not only this index.

---

## Lore Documents

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_lore_cosmology_history.md](aerus_lore_cosmology_history.md) | Cosmology (Primordial Thread, Vor'Athek) and history of the Four Ages | ~65 |
| [aerus_lore_geography.md](aerus_lore_geography.md) | Full geography: 5 continents and the Isles of Myr | ~104 |
| [aerus_lore_dome_factions.md](aerus_lore_dome_factions.md) | 4 major factions and the Dome (isekai mechanism) | ~85 |
| [aerus_lore_geopolitics_economy.md](aerus_lore_geopolitics_economy.md) | Active geopolitics, recent events (4212-4217 PC), and regional economy | ~236 |

---

## Mechanics Documents

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_mechanics_magic_isekai.md](aerus_mechanics_magic_isekai.md) | Magic system (Thread, levels, fusions, fragments, seals) and isekai travelers | ~119 |
| [aerus_mechanics_races.md](aerus_mechanics_races.md) | 5 complete playable races with comparative table | ~206 |
| [aerus_mechanics_systems.md](aerus_mechanics_systems.md) | Rumor system, Flame Seals, and faction reputation | ~141 |
| [aerus_mechanics_languages_crafting.md](aerus_mechanics_languages_crafting.md) | 6 playable languages and the crafting system | ~201 |

---

## Classes and Progression

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_base_classes.md](aerus_base_classes.md) | 8 organic classes and their progression structure | ~288 |
| [aerus_class_mutations.md](aerus_class_mutations.md) | Full formal class mutations at levels 25, 50, 75, and 100 | ~192 |

---

## NPCs

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_main_npcs.md](aerus_main_npcs.md) | Main narrative NPCs and key Porto Myr characters | ~165 |
| [aerus_npc_sheets.md](aerus_npc_sheets.md) | Expanded sheets for 12 NPCs with stats, motivations, secrets, and hooks | ~232 |

---

## GM Guide

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_gm_guide.md](aerus_gm_guide.md) | GM voice, tone examples by tension level, and technical guidance | ~229 |

---

## Missions and Arcs

| Document | Content | Lines |
|----------|---------|-------|
| [campaign_mission_structure.md](campaign_mission_structure.md) | General index and standard mission structure | ~39 |
| [campaign_missions_church_empire.md](campaign_missions_church_empire.md) | 3 missions for the Church of the Pure Flame and 3 for the Empire of Valdrek | ~62 |
| [campaign_missions_guild_children.md](campaign_missions_guild_children.md) | 3 missions for the Guild of Threads and 3 for the Children of the Broken Thread | ~157 |
| [campaign_mission_arcs.md](campaign_mission_arcs.md) | 4 main narrative arcs and convergence in The Last Chamber | ~122 |

---

## World Systems

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_travel.md](aerus_travel.md) | Travel system: encounter mechanics, canonical locations, main routes, terrain tables | ~151 |

---

## Technical Documentation

| Document | Content | Lines |
|----------|---------|-------|
| [PROJECT_CONTEXT_overview_stack.md](PROJECT_CONTEXT_overview_stack.md) | Project overview, stack, infrastructure, and admin hardware | ~120 |
| [PROJECT_CONTEXT_architecture_ard.md](PROJECT_CONTEXT_architecture_ard.md) | System architecture, data flow, WebSocket design, and functional/non-functional requirements | ~186 |
| [PROJECT_CONTEXT_adrs_sdd.md](PROJECT_CONTEXT_adrs_sdd.md) | ADRs and full software design documentation | ~131 |
| [PROJECT_CONTEXT_rules_roadmap.md](PROJECT_CONTEXT_rules_roadmap.md) | CLAUDE rules, LLM model strategy, context engineering, isekai, system rules, and roadmap | ~135 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Current implementation status | ~139 |
| [FRONTEND_SPEC.md](FRONTEND_SPEC.md) | Frontend specification | ~169 |

---

## Progression Rules

- Every 5 levels: the GM grants an organic power increase based on actions, class, and backstory.
- Every 25 levels (25, 50, 75, 100): formal class mutation. See [aerus_class_mutations.md](aerus_class_mutations.md).
- Level 100: Ascended state, the final point of progression.

---

## Runtime Sync Notes

- `lore/world.md` and `backend/config/world.md` must stay in sync.
- `backend/config/world_kernel.md` is the compact L0 summary for the GM and should be manually updated when faction or cosmology lore changes.
- `backend/config/bestiary.md` is the ChromaDB bestiary source.
- After editing `world.md` or `bestiary.md`, delete `backend/chroma_db/` to force re-ingestion.
- Use `make sync-lore` to automate the sync and cache invalidation in one step.

---

## New Config Files (March 2026)

| File | Purpose |
| --- | --- |
| `backend/config/reputation_gates.yaml` | Faction reputation thresholds and content unlocks per faction |
| `backend/config/rumors.yaml` | Base rumors with per-faction biased variant text |
| `backend/migrations/001–007_*.sql` | Versioned schema migration files for SQLite |

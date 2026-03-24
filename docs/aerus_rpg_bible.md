# AERUS RPG - Project Bible

> Version: 4.0 - Expanded modular structure (2026-03-23)
> This bible is split into smaller themed documents for easier navigation, maintenance, and model consumption.
> Always edit the corresponding themed document, not only this index.

---

## Lore Documents

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_lore_cosmology_history.md](aerus_lore_cosmology_history.md) | Cosmology (Primordial Thread, Vor'Athek) and history of the Four Ages | ~102 |
| [aerus_lore_geography.md](aerus_lore_geography.md) | Full geography: 5 continents and the Isles of Myr | ~105 |
| [aerus_lore_dome_factions.md](aerus_lore_dome_factions.md) | 4 major factions and the Dome (isekai mechanism) | ~108 |
| [aerus_lore_geopolitics_economy.md](aerus_lore_geopolitics_economy.md) | Active geopolitics, recent events (4212-4217 PC), and regional economy | ~267 |

---

## Mechanics Documents

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_mechanics_magic_isekai.md](aerus_mechanics_magic_isekai.md) | Magic system (Thread, levels, fusions, fragments, seals) and isekai travelers | ~146 |
| [aerus_mechanics_races.md](aerus_mechanics_races.md) | 5 complete playable races with comparative table | ~432 |
| [aerus_mechanics_systems.md](aerus_mechanics_systems.md) | Rumor system, Flame Seals, and faction reputation | ~320 |
| [aerus_mechanics_languages_crafting.md](aerus_mechanics_languages_crafting.md) | 6 playable languages and the crafting system | ~278 |

---

## Classes and Progression

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_base_classes.md](aerus_base_classes.md) | 8 organic classes and their progression structure | ~312 |
| [aerus_class_mutations.md](aerus_class_mutations.md) | Full formal class mutations at levels 25, 50, 75, and 100 | ~221 |

---

## NPCs

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_main_npcs.md](aerus_main_npcs.md) | Main narrative NPCs and key Porto Myr characters | ~191 |
| [aerus_npc_sheets.md](aerus_npc_sheets.md) | Expanded sheets for 12 NPCs with stats, motivations, secrets, and hooks | ~415 |

---

## GM Guide

| Document | Content | Lines |
|----------|---------|-------|
| [aerus_gm_guide.md](aerus_gm_guide.md) | GM voice, tone examples by tension level, and technical guidance | ~336 |

---

## Missions and Arcs

| Document | Content | Lines |
|----------|---------|-------|
| [campaign_mission_structure.md](campaign_mission_structure.md) | General index and standard mission structure | ~41 |
| [campaign_missions_church_empire.md](campaign_missions_church_empire.md) | 3 missions for the Church of the Pure Flame and 3 for the Empire of Valdrek | ~159 |
| [campaign_missions_guild_children.md](campaign_missions_guild_children.md) | 3 missions for the Guild of Threads and 3 for the Children of the Broken Thread | ~157 |
| [campaign_mission_arcs.md](campaign_mission_arcs.md) | 4 main narrative arcs and convergence in The Last Chamber | ~122 |

---

## Technical Documentation

| Document | Content | Lines |
|----------|---------|-------|
| [PROJECT_CONTEXT_overview_stack.md](PROJECT_CONTEXT_overview_stack.md) | Project overview, stack, infrastructure, and admin hardware | ~142 |
| [PROJECT_CONTEXT_architecture_ard.md](PROJECT_CONTEXT_architecture_ard.md) | System architecture, data flow, WebSocket design, and functional/non-functional requirements | ~227 |
| [PROJECT_CONTEXT_adrs_sdd.md](PROJECT_CONTEXT_adrs_sdd.md) | ADRs and full software design documentation | ~520 |
| [PROJECT_CONTEXT_rules_roadmap.md](PROJECT_CONTEXT_rules_roadmap.md) | CLAUDE rules, LLM model strategy, context engineering, isekai, system rules, and roadmap | ~492 |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Current implementation status | ~307 |
| [FRONTEND_SPEC.md](FRONTEND_SPEC.md) | Frontend specification | ~840 |

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

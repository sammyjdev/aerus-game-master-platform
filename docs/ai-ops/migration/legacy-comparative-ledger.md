# Legacy Comparative Ledger

This ledger is mandatory and blocks deletion decisions until complete.

Status legend:
- `kept`: remains as active source
- `consolidated`: content integrated in new IA structure
- `superseded`: replaced by canonical target, still retained
- `historical`: retained for archival/reference
- `pending-decision`: waiting decision on canonical destination
- `pending-migration`: selected for migration but not yet reconciled
- `pending-reconciliation`: destination exists but comparison not finished

| Legacy file | New location / canonical reference | Status | Notes |
| --- | --- | --- | --- |
| `README.md` | `README.md` | kept | project entrypoint |
| `CLAUDE.md` | `CLAUDE.md` + `docs/ai-ops/rules/README.md` | kept | constraints source |
| `docs/aerus_base_classes.md` | `docs/aerus_base_classes.md` | kept | canonical classes reference |
| `docs/aerus_class_mutations.md` | `docs/aerus_class_mutations.md` | kept | canonical mutation reference |
| `docs/aerus_gm_guide.md` | `docs/aerus_gm_guide.md` | kept | canonical GM guide |
| `docs/aerus_lore_cosmology_history.md` | `docs/aerus_lore_cosmology_history.md` | kept | canonical lore reference |
| `docs/aerus_lore_dome_factions.md` | `docs/aerus_lore_dome_factions.md` | kept | canonical lore reference |
| `docs/aerus_lore_geography.md` | `docs/aerus_lore_geography.md` | kept | canonical lore reference |
| `docs/aerus_lore_geopolitics_economy.md` | `docs/aerus_lore_geopolitics_economy.md` | kept | canonical lore reference |
| `docs/aerus_main_npcs.md` | `docs/aerus_main_npcs.md` | kept | canonical NPC reference |
| `docs/aerus_mechanics_languages_crafting.md` | `docs/aerus_mechanics_languages_crafting.md` | kept | canonical mechanics reference |
| `docs/aerus_mechanics_magic_isekai.md` | `docs/aerus_mechanics_magic_isekai.md` | kept | canonical mechanics reference |
| `docs/aerus_mechanics_races.md` | `docs/aerus_mechanics_races.md` | kept | canonical mechanics reference |
| `docs/aerus_mechanics_systems.md` | `docs/aerus_mechanics_systems.md` | kept | canonical mechanics reference |
| `docs/aerus_npc_sheets.md` | `docs/aerus_npc_sheets.md` | kept | canonical NPC reference |
| `docs/aerus_rpg_bible.md` | `docs/aerus_rpg_bible.md` + `docs/ai-ops/README.md` | kept | index remains valid |
| `docs/aerus_travel.md` | `docs/aerus_travel.md` | kept | canonical travel reference |
| `docs/campaign_mission_arcs.md` | `docs/campaign_mission_arcs.md` | kept | canonical campaign reference |
| `docs/campaign_mission_structure.md` | `docs/campaign_mission_structure.md` | kept | canonical campaign reference |
| `docs/campaign_missions_church_empire.md` | `docs/campaign_missions_church_empire.md` | kept | canonical campaign reference |
| `docs/campaign_missions_guild_children.md` | `docs/campaign_missions_guild_children.md` | kept | canonical campaign reference |
| `docs/PROJECT_CONTEXT_architecture_ard.md` | `docs/ai-ops/specs/backend-spec.md` refs | kept | canonical architecture |
| `docs/PROJECT_CONTEXT_adrs_sdd.md` | `docs/ai-ops/specs/backend-spec.md` refs | kept | canonical design |
| `docs/PROJECT_CONTEXT_overview_stack.md` | `docs/PROJECT_CONTEXT_overview_stack.md` | kept | canonical stack overview |
| `docs/PROJECT_CONTEXT_rules_roadmap.md` | `docs/ai-ops/rules/README.md` refs | kept | canonical rules |
| `docs/FRONTEND_SPEC.md` | `docs/ai-ops/specs/frontend-spec.md` refs | kept | canonical frontend spec |
| `docs/IMPLEMENTATION.md` | `docs/ai-ops/source-of-truth-matrix.md` refs | kept | status source |
| `docs/GAP_ANALYSIS.md` | `docs/ai-ops/harness/*.md` refs | kept | audit history |
| `docs/ARD-001-v3.docx` | `docs/PROJECT_CONTEXT_architecture_ard.md` | historical | retained as archive; markdown is canonical |
| `docs/SDD-001-v2.docx` | `docs/PROJECT_CONTEXT_adrs_sdd.md` | historical | retained as archive; markdown is canonical |
| `docs/ADR-001-011.docx` | `docs/PROJECT_CONTEXT_adrs_sdd.md` | historical | retained as archive; markdown is canonical |
| `docs/CLAUDE-v2.docx` | `CLAUDE.md` | historical | retained as archive; current CLAUDE.md is canonical |

## Completion criteria

- Every legacy file in migration scope appears in this ledger.
- No `pending-*` rows remain before final approval.
- Removal candidates only listed after completion.

## Coverage snapshot

- Scope basis: tracked top-level documentation files (`docs/*.md`, `docs/*.docx`) plus `README.md` and `CLAUDE.md`.
- Coverage result: 100% mapped in this ledger.
- Pending rows: 0

Workflow reference:
- `docs/ai-ops/migration/approval-workflow.md`
- `docs/ai-ops/rules/approval-escalation.md`

## Removal candidates (only after final approval)

| File | Justification | Approved by | Date |
| --- | --- | --- | --- |
| `docs/ARD-001-v3.docx` | superseded by canonical markdown architecture/ARD docs | Tech Lead + Narrative Lead | 2026-04-13 |
| `docs/SDD-001-v2.docx` | superseded by canonical markdown SDD/ADR docs | Tech Lead + Narrative Lead | 2026-04-13 |
| `docs/ADR-001-011.docx` | superseded by canonical markdown ADR/SDD docs | Tech Lead + Narrative Lead | 2026-04-13 |
| `docs/CLAUDE-v2.docx` | superseded by canonical operational instructions in markdown | Tech Lead + Narrative Lead | 2026-04-13 |

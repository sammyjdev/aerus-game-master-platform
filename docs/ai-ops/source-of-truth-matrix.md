# Source Of Truth Matrix

This matrix maps legacy assets to the new IA-first operating model.

Status values:
- `authoritative`: canonical source
- `supporting`: useful reference, non-canonical
- `historical`: retained, not primary
- `pending-mapping`: must be reconciled before migration close

| Domain | Canonical file(s) | Supporting file(s) | Legacy/historical | Status | Owner |
| --- | --- | --- | --- | --- | --- |
| Project entry | `README.md` | `CLAUDE.md` | - | authoritative | Tech Lead |
| Documentation index | `docs/aerus_rpg_bible.md` | `docs/IMPLEMENTATION.md` | - | authoritative | Docs Lead |
| Architecture and ARD | `docs/PROJECT_CONTEXT_architecture_ard.md` | `docs/PROJECT_CONTEXT_adrs_sdd.md` | `docs/ARD-001-v3.docx` | authoritative | Backend Lead |
| Engineering constraints | `docs/PROJECT_CONTEXT_rules_roadmap.md` | `CLAUDE.md` | `docs/CLAUDE-v2.docx` | authoritative | Tech Lead |
| Frontend spec | `docs/FRONTEND_SPEC.md` | `docs/IMPLEMENTATION.md` | - | authoritative | Frontend Lead |
| Implementation status | `docs/IMPLEMENTATION.md` | `docs/GAP_ANALYSIS.md` | - | authoritative | Tech Lead |
| Lore canonical | `lore/world.md`, `lore/bestiary.md` | themed lore docs in `docs/` | - | authoritative | Narrative Lead |
| Runtime lore/config | `backend/config/world.md`, `backend/config/campaign.yaml`, `backend/config/travel.yaml` | `scripts/sync_lore.sh` | - | authoritative | Backend Lead |
| WS contracts backend | `backend/src/ws_contracts.py` | `backend/src/models.py` | - | authoritative | Backend Lead |
| WS contracts frontend | `frontend/src/types/wsContracts.ts` | `frontend/src/types/index.ts` | - | authoritative | Frontend Lead |
| GM behavior harness | `backend/eval/gm_eval.py` | `backend/eval/gm_eval_runtime.py`, `backend/eval/gm_eval_reporting.py` | eval history logs | authoritative | QA/AI Lead |
| CI test gate | `.github/workflows/test.yml` | `.github/workflows/deploy.yml` | - | authoritative | DevOps Lead |
| ADR docx bundle | - | `docs/PROJECT_CONTEXT_adrs_sdd.md` | `docs/ADR-001-011.docx`, `docs/SDD-001-v2.docx` | pending-mapping | Tech Lead |

## Mandatory closing condition

No file can be tagged for removal until it is registered in:
- `docs/ai-ops/migration/legacy-comparative-ledger.md`

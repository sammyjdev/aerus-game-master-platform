# Harness Gates Matrix

| Change type                      | Required gate        | Command baseline                                                                 | Block condition                                |
| -------------------------------- | -------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------- |
| Docs-only IA organization        | smoke-docs           | link/integrity checks + comparative ledger update                                | missing mappings                               |
| Backend gameplay behavior        | core                 | `cd backend && .venv/Scripts/python eval/gm_eval.py`                             | hard-fail labels or pass drop beyond threshold |
| High-risk behavior/model routing | extended             | `cd backend && AERUS_EVAL_PROFILE=extended .venv/Scripts/python eval/gm_eval.py` | new regressions not waived                     |
| WS contract changes              | core + frontend test | backend eval + `cd frontend && npm test`                                         | backend/frontend contract mismatch             |
| Lore-impacting behavior          | core at minimum      | eval run on impacted scenarios                                                   | lore regressions in relevant scenarios         |

## Minimum thresholds

- No unresolved hard-fail labels.
- No net-new regression without waiver record.
- Comparative history entry must be attached for core/extended runs.

## Approval authority

- Final removal approval: Tech Lead and Narrative Lead (joint sign-off).
- Waived regression approval: Backend Lead and QA/AI Lead.
- Escalation trigger: unresolved blocked state beyond 5 days.

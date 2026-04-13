# AI Documentation Operations

This directory defines the operational IA-first documentation model for Aerus.

Core goals:

- no information loss during migration
- single discovery path for humans and agents
- task-oriented execution with explicit playbooks
- validation gates connected to existing GM harness

## Non-destructive migration policy

No legacy file is deleted until all items are reconciled in:

- `docs/ai-ops/migration/legacy-comparative-ledger.md`

Deletion decisions happen only after explicit final approval.

## Navigation

- Source of truth: `docs/ai-ops/source-of-truth-matrix.md`
- Specs: `docs/ai-ops/specs/README.md`
- Rules: `docs/ai-ops/rules/README.md`
- Approval policy: `docs/ai-ops/rules/approval-escalation.md`
- Agent playbooks: `docs/ai-ops/agents/README.md`
- Skills: `docs/ai-ops/skills/README.md`
- Harness: `docs/ai-ops/harness/README.md`
- Migration controls: `docs/ai-ops/migration/migration-checklist.md`
- Agent validation evidence: `docs/ai-ops/evidence/agent-validation-log.md`

## Execution cross-reference

| Playbook           | Skills involved                                   | Required gates                                  |
| ------------------ | ------------------------------------------------- | ----------------------------------------------- |
| backend-feature    | state-delta-safety, gm-eval-triage                | backend tests + harness core/extended as needed |
| frontend-feature   | frontend-store-websocket-flow, ws-contract-parity | frontend test + build                           |
| ws-contract-change | ws-contract-parity                                | backend/frontend WS checks + harness core       |
| lore-change        | lore-sync, travel-encounter-integrity             | sync checks + scenario validation               |
| migration-change   | all as needed                                     | ledger completeness + migration guard           |
| bugfix             | scenario-dependent                                | targeted tests + risk-based harness             |

## Required execution order

1. Freeze scope and confirm no-deletion mode.
2. Use source-of-truth matrix to route work.
3. Execute tasks through the matching agent playbook.
4. Apply required skill cards.
5. Run harness gates.
6. Update comparative ledger.
7. Run final comparison and only then decide removals.

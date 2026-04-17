# Agent Playbooks

All migration tasks must run through one of these playbooks.

## Playbooks

- `docs/ai-ops/agents/backend-feature-playbook.md`
- `docs/ai-ops/agents/frontend-feature-playbook.md`
- `docs/ai-ops/agents/ws-contract-change-playbook.md`
- `docs/ai-ops/agents/lore-change-playbook.md`
- `docs/ai-ops/agents/migration-change-playbook.md`
- `docs/ai-ops/agents/bugfix-playbook.md`

## Failure and rollback

If a playbook run fails mid-execution:

1. Preserve evidence of failure in `docs/ai-ops/evidence/agent-validation-log.md`.
2. Revert only uncommitted partial work if needed.
3. Re-run from the failed playbook step, not from an unrelated playbook.
4. Do not bypass required gates after retry.

## Output requirement

Each run must produce a short evidence entry in:

- `docs/ai-ops/evidence/agent-validation-log.md`

# Approval And Escalation Policy

## Removal approval authority

Deletion approval requires joint sign-off from:
- Tech Lead
- Narrative Lead

Self-approval is not allowed.

Authority registry:
- `docs/ai-ops/rules/approval-authority-registry.json`

## Preconditions for approval

1. Comparative ledger has no `pending` rows.
2. Candidate appears in both legacy mapping and removal table.
3. Removal table has justification, approver names, and date.

## Escalation policy

- New regression unresolved for 3 business days: open escalation issue.
- If unresolved by agreed ETA: mandatory weekly review until closure.

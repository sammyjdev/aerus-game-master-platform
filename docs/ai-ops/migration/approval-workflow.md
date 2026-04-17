# Migration Approval Workflow

```mermaid
flowchart TD
  A[Start migration task] --> B[Map legacy file in comparative ledger]
  B --> C{Status resolved?}
  C -- no --> B
  C -- yes --> D[Run required playbook and skills]
  D --> E[Run harness/test gates]
  E --> F{Any failures?}
  F -- yes --> G[Fix and rerun gates]
  G --> E
  F -- no --> H[Final comparative check 100 percent coverage]
  H --> I{Any pending rows?}
  I -- yes --> B
  I -- no --> J[Joint approval Tech Lead and Narrative Lead]
  J --> K[Optional deletion batch in later PR]
```

## State transitions

- `pending-decision` -> `historical` or `consolidated` or `kept`
- `pending-reconciliation` -> `superseded` or `kept`
- `pending-migration` -> `consolidated`

No transition to removal without joint approval.

# Backend Feature Playbook

## Use when

Changing backend behavior, endpoints, orchestration, persistence, or evaluation logic.

## Inputs

- linked spec(s)
- impacted module list
- expected behavior and acceptance criteria

## Steps

1. Read relevant specs and rules.
2. Implement change in constrained modules.
3. Run backend tests.
4. If GM behavior changed, run harness tier required by risk.
5. Update source-of-truth matrix if new doc asset appears.
6. Register evidence in validation log.

## Required gates

- `pytest` pass for affected backend scope
- WS parity check if payload/schema changed
- Harness tier pass for gameplay behavior changes

## Definition of done

- behavior implemented
- tests passing
- evidence entry recorded
- no legacy file deleted

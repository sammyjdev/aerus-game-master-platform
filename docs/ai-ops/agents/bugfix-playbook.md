# Bugfix Playbook

## Use when

Fixing defects in backend, frontend, contracts, or migration tooling.

## Inputs

- reproducible symptom
- suspected scope

## Steps

1. Reproduce and capture baseline.
2. Implement minimal fix.
3. Run targeted tests first, then broader gate if risk requires.
4. Confirm no regression in adjacent flows.
5. Record fix evidence and impacted artifacts.

## Required gates

- targeted tests pass
- no new contract break
- harness check if gameplay behavior changed

## Definition of done

- defect no longer reproducible
- tests and checks pass
- evidence recorded
- no legacy file deleted

# Skill Cards Detail

## lore-sync

- use when: canonical lore changed
- do not use when: only UI text changed
- required input: changed lore files
- output: synced runtime files and verification note

## ws-contract-parity

- use when: websocket payload changes
- do not use when: HTTP-only changes
- required input: message type list
- output: mirrored backend/frontend schema update

## migration-runner-and-sql

- use when: adding migration files or schema behavior
- do not use when: docs-only updates
- required input: migration intent and rollback note
- output: migration + tests + compatibility statement

## gm-eval-triage

- use when: behavior quality changed in GM output
- do not use when: static docs-only updates
- required input: changed behavior scenario
- output: profile selection, run result, failure interpretation

## state-delta-safety

- use when: applying new delta fields in gameplay loop
- do not use when: read-only analytics changes
- required input: new delta schema
- output: safe apply path + invariant checks

## frontend-store-websocket-flow

- use when: store shape or WS handlers changed
- do not use when: style-only changes
- required input: event and state diff
- output: parser, store, and UI path aligned

## reputation-rumor-gates

- use when: faction systems change
- do not use when: unrelated combat-only features
- required input: reputation thresholds and rumor ids
- output: threshold handling and per-player delivery verified

## travel-encounter-integrity

- use when: travel routes/tables change
- do not use when: local narrative text only
- required input: route/table changes
- output: route keys valid, encounter scale behavior validated

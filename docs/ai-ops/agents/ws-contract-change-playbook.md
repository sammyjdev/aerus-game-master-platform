# WS Contract Change Playbook

## Use when

Adding/removing/updating outbound WS message structures.

## Inputs

- contract diff proposal
- impacted message types

## Steps

1. Update backend schema in `backend/src/ws_contracts.py`.
2. Update frontend schema in `frontend/src/types/wsContracts.ts`.
3. Validate backend send path and frontend safe parse path.
4. Run backend and frontend tests touching WS flow.
5. Record exact contract delta in evidence log.

## Required gates

- backend tests for WS paths
- frontend tests for parser/store integration
- explicit parity check complete

## Definition of done

- backend and frontend schemas aligned
- parser and sender paths validated
- evidence recorded
- no legacy file deleted

# Migration Change Playbook

## Use when

Reorganizing documentation into IA-first structure.

## Inputs

- source-of-truth matrix
- migration target structure

## Steps

1. Create new structure in parallel (never in-place destructive move).
2. Map each legacy asset in comparative ledger.
3. Mark status per file: kept, consolidated, superseded, historical, pending.
4. Validate link integrity and discoverability.
5. Produce final comparative report before any deletion decision.

## Required gates

- comparative ledger coverage 100%
- zero deletions during migration
- final review approval

## Definition of done

- new structure operational
- full traceability report complete
- deletion decisions deferred until final approval

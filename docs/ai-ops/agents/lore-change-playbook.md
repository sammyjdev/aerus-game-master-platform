# Lore Change Playbook

## Use when

Editing lore, world canon, bestiary, or travel narrative data.

## Inputs

- lore change set
- expected runtime impact

## Steps

1. Apply edits in `lore/` canonical sources.
2. Sync to runtime config with `make sync-lore`.
3. Perform required retrieval cache refresh if applicable.
4. Spot-check runtime files and retrieval behavior.
5. Record migration trace and evidence.

## Required gates

- sync complete
- runtime copy verified
- harness scenario run if change affects GM behavior

## Definition of done

- canonical and runtime copies aligned
- verification logged
- no legacy file deleted

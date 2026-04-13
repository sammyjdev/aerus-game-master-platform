# Lore To Runtime Sync Spec

Canonical authored lore:

- `lore/world.md`
- `lore/bestiary.md`

Runtime operational copy:

- `backend/config/world.md`
- `backend/config/bestiary_t1.md` ... `backend/config/bestiary_t5.md`

## Required behavior

1. Lore edits are applied in `lore/` first.
2. Runtime copy is synchronized before gameplay validation.
3. Chroma cache is invalidated when required by lore changes.

## Verification criteria

- Sync command run: `make sync-lore`.
- Post-sync content spot-check in runtime config files.
- If world/bestiary changed, retrieval cache refresh performed.

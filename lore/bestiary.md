# Aerus RPG - Complete Bestiary

> Canonical source split by tier for easier navigation and editing.
> All files are concatenated automatically for ChromaDB ingestion.

## Tier Index

| File | Tier | Level Range | Creatures |
| --- | --- | --- | --- |
| [bestiary_t1.md](bestiary_t1.md) | Tier 1 - Scum | 1-30 | 20 |
| [bestiary_t2.md](bestiary_t2.md) | Tier 2 - Tacticians | 31-70 | 20 |
| [bestiary_t3.md](bestiary_t3.md) | Tier 3 - Predators | 71-110 | 16 |
| [bestiary_t4.md](bestiary_t4.md) | Tier 4 - Lords | 111-140 | 12 |
| [bestiary_t5.md](bestiary_t5.md) | Tier 5 - Calamities | 141-150 | 4 |

## Metadata Format

```md
**Tier:** N | **Level:** X-Y | **Type:** Corrupted/Natural/...
**Habitat:** ... | **Element:** ...
```

> To add creatures, edit the file for the corresponding tier.
> After editing, delete `backend/chroma_db/` to force re-ingestion.

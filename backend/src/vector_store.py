"""
vector_store.py - The ONLY module with direct ChromaDB access.
Responsibility: ingest bestiary and world lore, then retrieve relevant semantic context.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from .infrastructure.config.config_loader import load_bestiary_md, load_world_md
from .models import LoreResult

logger = logging.getLogger(__name__)

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "aerus_lore"

_WORLD_LORE_SOURCE = "world_lore"
_BESTIARY_SOURCE = "bestiary"
_SKIP_SECTIONS = {"VI"}  # Bestiary - already handled by ingest_bestiary
_MAX_CHUNK_CHARS = 1500

_SECTION_MAP = {
    "I": "cosmology",
    "II": "history",
    "III": "geography",
    "IV": "factions",
    "V": "magic",
    "VII": "prophecies",
    "VIII": "languages_culture",
}

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _section_name_to_id(title: str) -> str:
    for numeral, sid in _SECTION_MAP.items():
        if title.startswith(f"{numeral}."):
            return sid
    return re.sub(r"[^a-z0-9]", "_", title.lower()).strip("_")


def _parse_bestiary_entries(bestiary_md: str) -> list[dict[str, Any]]:
    """
    Parse bestiary.md into creature blocks.
    Each creature starts with '## ' and ends at the next '## ' or file end.
    """
    entries: list[dict[str, Any]] = []
    blocks = re.split(r"\n(?=## )", bestiary_md)

    for block in blocks:
        block = block.strip()
        if not block.startswith("## "):
            continue

        lines = block.split("\n")
        name = lines[0].replace("## ", "").strip()

        tier = _extract_field(block, r"Tier[:\s]+(\d+|[^\n]+)")
        level_range = _extract_field(block, r"Level[:\s]+([^\n]+)")
        habitat = _extract_field(block, r"Habitat[:\s]+([^\n]+)")
        element = _extract_field(block, r"Element[:\s]+([^\n]+)")
        creature_type = _extract_field(block, r"Type[:\s]+([^\n]+)")

        entry_id = re.sub(r"[^a-z0-9_]", "_", name.lower())

        entries.append(
            {
                "id": entry_id,
                "document": block,
                "metadata": {
                    "name": name,
                    "tier": tier or "unknown",
                    "level_range": level_range or "unknown",
                    "habitat": habitat or "unknown",
                    "element": element or "unknown",
                    "type": creature_type or "unknown",
                    "source": _BESTIARY_SOURCE,
                },
            }
        )

    logger.info("Parsed %d creatures from the bestiary", len(entries))
    return entries


def _extract_field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


async def ingest_bestiary() -> int:
    """
    Ingest bestiary.md into ChromaDB.
    Idempotent - checks whether it has already been ingested.
    Returns the number of ingested documents.
    """
    collection = _get_collection()
    existing = collection.get(where={"source": _BESTIARY_SOURCE}, limit=1)
    if existing and existing.get("ids"):
        logger.info("Bestiary already ingested - skipping")
        return collection.count()

    bestiary_md = load_bestiary_md()
    entries = _parse_bestiary_entries(bestiary_md)

    if not entries:
        logger.warning("No creatures found in bestiary.md")
        return 0

    batch_size = 50
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        collection.add(
            ids=[e["id"] for e in batch],
            documents=[e["document"] for e in batch],
            metadatas=[e["metadata"] for e in batch],
        )

    logger.info("Bestiary ingestion complete: %d creatures in ChromaDB", len(entries))
    return len(entries)


def _is_skipped_section(title: str) -> bool:
    """Return True if the section's Roman numeral is in _SKIP_SECTIONS."""
    return any(title.startswith(f"{numeral}.") for numeral in _SKIP_SECTIONS)


def _section_to_entries(block: str, title: str, section_id: str) -> list[dict[str, Any]]:
    """Return one entry for short blocks, or one per subsection for longer blocks."""
    if len(block) <= _MAX_CHUNK_CHARS:
        meta = {"name": title, "section": section_id, "source": _WORLD_LORE_SOURCE}
        return [{"id": f"world_{section_id}", "document": block, "metadata": meta}]

    entries: list[dict[str, Any]] = []
    for j, sub_block in enumerate(re.split(r"\n(?=### )", block)):
        sub_block = sub_block.strip()
        if not sub_block:
            continue
        sub_name = sub_block.split("\n", 1)[0].lstrip("# ").strip() or title
        meta = {"name": sub_name, "section": section_id, "source": _WORLD_LORE_SOURCE}
        entries.append({"id": f"world_{section_id}_{j}", "document": sub_block, "metadata": meta})
    return entries


def _parse_world_sections(world_md: str) -> list[dict[str, Any]]:
    """
    Parse world.md into sections and subsections as individual documents.
    Sections listed in _SKIP_SECTIONS are ignored.
    """
    entries: list[dict[str, Any]] = []

    for block in re.split(r"\n(?=## )", world_md):
        block = block.strip()
        if not block.startswith("## "):
            continue

        title = block.split("\n")[0].replace("## ", "").strip()
        if _is_skipped_section(title):
            continue

        section_id = _section_name_to_id(title)
        entries.extend(_section_to_entries(block, title, section_id))

    logger.info("Parsed %d world-lore entries", len(entries))
    return entries


async def ingest_world_lore() -> int:
    """
    Ingest world.md into ChromaDB.
    Idempotent - checks whether it has already been ingested.
    Returns the number of ingested documents.
    """
    await asyncio.sleep(0)

    collection = _get_collection()
    existing = collection.get(where={"source": _WORLD_LORE_SOURCE}, limit=1)
    if existing and existing.get("ids"):
        logger.info("World lore already ingested - skipping")
        return collection.count()

    world_md = load_world_md()
    entries = _parse_world_sections(world_md)

    if not entries:
        logger.warning("No sections found in world.md")
        return 0

    batch_size = 50
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        collection.add(
            ids=[e["id"] for e in batch],
            documents=[e["document"] for e in batch],
            metadatas=[e["metadata"] for e in batch],
        )

    logger.info("World lore ingestion complete: %d documents in ChromaDB", len(entries))
    return len(entries)


async def retrieve_lore(query: str, n_results: int = 3) -> LoreResult:
    """
    Retrieve relevant lore through semantic search.
    Used by context_builder to populate the lore layer.
    """
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("ChromaDB is empty - run ingest_bestiary() first")
        return LoreResult()

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
    )
    documents = results.get("documents", [[]])[0] or []
    metadatas = results.get("metadatas", [[]])[0] or []
    return LoreResult(documents=documents, metadatas=metadatas)

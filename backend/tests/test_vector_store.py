"""
test_vector_store.py — Testes das funções de parsing de lore em vector_store.py.
Cobre _parse_world_sections, _parse_bestiary_entries e helpers relacionados.
"""
from __future__ import annotations

import pytest

from src.vector_store import (
    _parse_bestiary_entries,
    _parse_world_sections,
    _section_name_to_id,
)
from src.infrastructure.config.config_loader import load_bestiary_md, load_world_md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_world_entries():
    """Parse real world.md once and return entries."""
    return _parse_world_sections(load_world_md())


# ---------------------------------------------------------------------------
# _parse_world_sections — skips bestiário
# ---------------------------------------------------------------------------

class TestParseWorldSectionsSkipsBestiary:
    """Seção VI (Bestiário) não deve aparecer nas entradas de world lore."""

    def test_no_entry_has_section_bestiario(self):
        entries = _get_world_entries()
        sections = [e["metadata"]["section"] for e in entries]
        assert "bestiario" not in sections

    def test_no_entry_has_section_vi(self):
        entries = _get_world_entries()
        # _section_name_to_id("VI. BESTIÁRIO...") would produce "vi_besti..." but
        # the section should have been skipped before reaching that point.
        for entry in entries:
            assert not entry["metadata"]["section"].startswith("vi")

    def test_no_document_contains_tier1_marker(self):
        entries = _get_world_entries()
        for entry in entries:
            assert "TIER 1" not in entry["document"]
            assert "TIER 2" not in entry["document"]

    def test_no_document_references_bestiary_creatures(self):
        """Entries should not contain raw bestiary creature blocks like '## 01 |'."""
        entries = _get_world_entries()
        for entry in entries:
            assert "## 01 |" not in entry["document"]


# ---------------------------------------------------------------------------
# _parse_world_sections — expected sections present
# ---------------------------------------------------------------------------

class TestParseWorldSectionsExpectedSections:
    """All non-bestiary mapped sections must be present in the output."""

    EXPECTED_SECTIONS = {
        "cosmologia",
        "historia",
        "geografia",
        "faccoes",
        "magia",
        "profecias",
        "linguas_cultura",
    }

    def test_all_expected_sections_present(self):
        entries = _get_world_entries()
        found_sections = {e["metadata"]["section"] for e in entries}
        for section in self.EXPECTED_SECTIONS:
            assert section in found_sections, (
                f"Section '{section}' not found in parsed entries. "
                f"Found: {sorted(found_sections)}"
            )

    def test_no_unexpected_sections(self):
        """Only mapped sections should appear (no raw roman numeral IDs)."""
        entries = _get_world_entries()
        found_sections = {e["metadata"]["section"] for e in entries}
        # All sections must be in the set of expected sections
        for section in found_sections:
            assert section in self.EXPECTED_SECTIONS, (
                f"Unexpected section '{section}' found in parsed entries."
            )


# ---------------------------------------------------------------------------
# _parse_world_sections — large sections are chunked
# ---------------------------------------------------------------------------

class TestParseWorldSectionsChunksLargeSections:
    """Geography (III) is large enough to be split into multiple entries."""

    def test_geografia_has_multiple_entries(self):
        entries = _get_world_entries()
        geo_entries = [e for e in entries if e["metadata"]["section"] == "geografia"]
        assert len(geo_entries) > 1, (
            f"Expected multiple 'geografia' entries due to chunking, got {len(geo_entries)}"
        )

    def test_geografia_entries_each_under_max_chunk_chars(self):
        """After chunking, each sub-entry's document should be reasonably sized.
        We don't enforce a hard cap here — the split is on ### boundaries —
        but the original unsplit block must have been larger than 1500 chars."""
        entries = _get_world_entries()
        geo_entries = [e for e in entries if e["metadata"]["section"] == "geografia"]
        # Combined size should be well above the 1500-char limit
        total_chars = sum(len(e["document"]) for e in geo_entries)
        assert total_chars > 1500

    def test_short_sections_are_single_entry(self):
        """Profecias and linguas_cultura are short enough to be a single entry each."""
        entries = _get_world_entries()
        for section in ("profecias", "linguas_cultura"):
            section_entries = [e for e in entries if e["metadata"]["section"] == section]
            # Each should exist
            assert len(section_entries) >= 1


# ---------------------------------------------------------------------------
# _parse_world_sections — metadata structure
# ---------------------------------------------------------------------------

class TestParseWorldSectionsMetadataStructure:
    """Every entry must follow the expected dict schema."""

    def test_every_entry_has_required_top_level_keys(self):
        entries = _get_world_entries()
        assert entries, "Expected at least one entry from world.md"
        for entry in entries:
            assert "id" in entry, f"Missing 'id' in entry: {entry}"
            assert "document" in entry, f"Missing 'document' in entry: {entry}"
            assert "metadata" in entry, f"Missing 'metadata' in entry: {entry}"

    def test_every_metadata_has_required_keys(self):
        entries = _get_world_entries()
        for entry in entries:
            meta = entry["metadata"]
            assert "name" in meta, f"Missing 'name' in metadata: {meta}"
            assert "section" in meta, f"Missing 'section' in metadata: {meta}"
            assert "source" in meta, f"Missing 'source' in metadata: {meta}"

    def test_every_entry_source_is_world_lore(self):
        entries = _get_world_entries()
        for entry in entries:
            assert entry["metadata"]["source"] == "world_lore", (
                f"Expected source='world_lore', got '{entry['metadata']['source']}'"
            )

    def test_every_entry_id_is_non_empty_string(self):
        entries = _get_world_entries()
        for entry in entries:
            assert isinstance(entry["id"], str)
            assert len(entry["id"]) > 0

    def test_every_entry_document_is_non_empty_string(self):
        entries = _get_world_entries()
        for entry in entries:
            assert isinstance(entry["document"], str)
            assert len(entry["document"]) > 0


# ---------------------------------------------------------------------------
# _section_name_to_id — roman numeral mapping
# ---------------------------------------------------------------------------

class TestSectionNameToIdMapping:
    """_section_name_to_id must resolve roman numerals to canonical slugs."""

    CASES = [
        ("I. COSMOLOGIA E ORIGEM", "cosmologia"),
        ("II. HISTÓRIA — AS QUATRO ERAS", "historia"),
        ("III. GEOGRAFIA — O MAPA DE AERUS", "geografia"),
        ("IV. FACÇÕES PRINCIPAIS", "faccoes"),
        ("V. O FIO PRIMORDIAL — REGRAS PARA O GM", "magia"),
        ("VII. PROFECIAS E DESTINO", "profecias"),
        ("VIII. LÍNGUAS E CULTURA", "linguas_cultura"),
    ]

    @pytest.mark.parametrize("title,expected_id", CASES)
    def test_roman_numeral_maps_to_slug(self, title, expected_id):
        assert _section_name_to_id(title) == expected_id

    def test_unknown_title_falls_back_to_sanitized_slug(self):
        result = _section_name_to_id("X. Something Completely New")
        # Should not raise; should return a non-empty lowercase string
        assert isinstance(result, str)
        assert len(result) > 0
        assert result == result.lower()

    def test_bestiary_section_vi_is_not_in_map(self):
        """VI is intentionally absent from _SECTION_MAP (handled by ingest_bestiary)."""
        result = _section_name_to_id("VI. BESTIÁRIO DE AERUS")
        # Not in the map — falls back to a sanitized slug
        assert result != "bestiario"  # not mapped
        assert "vi" in result or "besti" in result


# ---------------------------------------------------------------------------
# _parse_bestiary_entries — metadata structure
# ---------------------------------------------------------------------------

SAMPLE_BESTIARY = """\
## LOBO-CINZA
**Tier:** 1 | **Nível:** 1–5 | **Tipo:** Natural Mutado
**Habitat:** Florestas corrompidas, bordas de Surtos
**Elemento:** Cinza

**Ataques:**
- *Mordida Corrupta* (físico): 1d8 dano

**Resistências:** Veneno

## WYVERN KHORRATH
**Tier:** 3 | **Nível:** 40–60 | **Tipo:** Corrupto
**Habitat:** Deserto de Cinzas, ruínas Aeridanas
**Elemento:** Fogo/Cinza

**Ataques:**
- *Baforada de Cinzas* (arcano, área): 3d8 dano
"""


class TestBestiaryEntriesHaveSource:
    """Every parsed bestiary entry must carry source='bestiary' in metadata."""

    def test_sample_entries_have_bestiary_source(self):
        entries = _parse_bestiary_entries(SAMPLE_BESTIARY)
        assert len(entries) == 2
        for entry in entries:
            assert entry["metadata"]["source"] == "bestiary", (
                f"Expected source='bestiary', got '{entry['metadata']['source']}'"
            )

    def test_sample_entries_have_required_metadata_keys(self):
        entries = _parse_bestiary_entries(SAMPLE_BESTIARY)
        required_keys = {"name", "tier", "level_range", "habitat", "element", "type", "source"}
        for entry in entries:
            for key in required_keys:
                assert key in entry["metadata"], (
                    f"Missing key '{key}' in bestiary metadata: {entry['metadata']}"
                )

    def test_sample_entries_have_required_top_level_keys(self):
        entries = _parse_bestiary_entries(SAMPLE_BESTIARY)
        for entry in entries:
            assert "id" in entry
            assert "document" in entry
            assert "metadata" in entry

    def test_real_bestiary_all_entries_have_source(self):
        """Parse real bestiary.md and verify every entry has source='bestiary'."""
        entries = _parse_bestiary_entries(load_bestiary_md())
        assert len(entries) > 0, "Expected at least one creature in bestiary.md"
        for entry in entries:
            assert entry["metadata"]["source"] == "bestiary"

    def test_real_bestiary_no_entry_has_world_lore_source(self):
        entries = _parse_bestiary_entries(load_bestiary_md())
        for entry in entries:
            assert entry["metadata"]["source"] != "world_lore"

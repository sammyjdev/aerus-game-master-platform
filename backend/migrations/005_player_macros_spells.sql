-- Migration 005: Player macros and spell aliases
-- Adds macro storage and spell alias mapping for QoL features.

ALTER TABLE players ADD COLUMN macros_json        TEXT NOT NULL DEFAULT '[]';
ALTER TABLE players ADD COLUMN spell_aliases_json TEXT NOT NULL DEFAULT '{}';

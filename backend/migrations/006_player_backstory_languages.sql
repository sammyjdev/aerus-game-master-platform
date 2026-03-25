-- Migration 006: Backstory change flag and language proficiencies
-- Adds flag for recent backstory edits (context injection) and known languages list.

ALTER TABLE players ADD COLUMN backstory_changed_recently INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN languages_json             TEXT NOT NULL DEFAULT '["common_tongue"]';

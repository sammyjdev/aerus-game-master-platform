-- Migration 003: Conditions buff/debuff classification
-- Adds is_buff flag to conditions so the GM can distinguish buffs from debuffs.

ALTER TABLE conditions ADD COLUMN is_buff INTEGER NOT NULL DEFAULT 0;

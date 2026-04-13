-- Migration 010: Flame Seal tracking
-- Adds the flame_seal column to players for Church of the Pure Flame licensing system.
-- Values: NULL (no seal), 'common', 'trade', 'high_flame', 'null_seal', 'conclave'
ALTER TABLE players ADD COLUMN flame_seal TEXT DEFAULT NULL;

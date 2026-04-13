-- Migration 008: Isekai rooting tracking for isekaid players
ALTER TABLE players ADD COLUMN days_in_world   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN rooting_stage   INTEGER NOT NULL DEFAULT 0;
-- rooting_stage: 0 = unrooted, 1 = anchored, 2 = resonant, 3 = merged, 4 = sovereign
-- days_in_world: incremented each in-game day (via time_manager or state delta)

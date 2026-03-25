-- Migration 007: Per-player episodic memory
-- Stores structured significant events per player with importance scoring.
-- Used by context_builder for personalized GM context and by B5 for mutation tracking.

CREATE TABLE IF NOT EXISTS player_episodes (
    episode_id      TEXT PRIMARY KEY,
    player_id       TEXT NOT NULL REFERENCES players(player_id),
    turn_number     INTEGER NOT NULL,
    event_type      TEXT NOT NULL,
    description     TEXT NOT NULL,
    importance      INTEGER NOT NULL DEFAULT 1,
    created_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_player_episodes_player
    ON player_episodes (player_id, importance DESC, turn_number DESC);

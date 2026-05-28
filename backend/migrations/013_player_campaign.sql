-- Migration 013: Per-player campaign scope
-- campaign_id groups players into a shared session for WS broadcast routing.
-- All existing players join 'default' so single-campaign deployments keep working unchanged.

ALTER TABLE players ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_players_campaign ON players(campaign_id);

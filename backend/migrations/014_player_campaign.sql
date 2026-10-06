-- Migration 014: Reconcile both historical version-13 schema changes.
-- campaign_id groups players into a shared session for WS broadcast routing.
-- All existing players join 'default' so single-campaign deployments keep working unchanged.
-- Some databases recorded 013_player_campaign.sql without applying magic_level.

ALTER TABLE players ADD COLUMN magic_level INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_players_campaign ON players(campaign_id);

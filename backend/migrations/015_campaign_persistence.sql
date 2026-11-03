-- Scope previously global runtime data under the default campaign.
ALTER TABLE history ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE world_memory ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE arc_memory ADD COLUMN campaign_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX idx_history_campaign_turn ON history(campaign_id, turn_number DESC, created_at DESC);
CREATE INDEX idx_world_memory_campaign_time ON world_memory(campaign_id, updated_at DESC);
CREATE INDEX idx_arc_memory_campaign_time ON arc_memory(campaign_id, updated_at DESC);

CREATE TABLE world_state_scoped (
    key TEXT,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (campaign_id, key)
);
INSERT INTO world_state_scoped (key, value, updated_at) SELECT key, value, updated_at FROM world_state;
DROP TABLE world_state;
ALTER TABLE world_state_scoped RENAME TO world_state;

CREATE TABLE quest_flags_scoped (
    flag_key TEXT,
    flag_value TEXT NOT NULL,
    updated_at REAL NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (campaign_id, flag_key)
);
INSERT INTO quest_flags_scoped (flag_key, flag_value, updated_at) SELECT flag_key, flag_value, updated_at FROM quest_flags;
DROP TABLE quest_flags;
ALTER TABLE quest_flags_scoped RENAME TO quest_flags;


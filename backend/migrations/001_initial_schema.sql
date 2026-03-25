-- Migration 001: Full initial schema (current baseline)
-- Includes all columns as of 2026-03-25, including columns added via inline migrations.
-- For fresh databases this creates everything at once.
-- Migrations 002-006 handle upgrading existing databases that predate those columns.

CREATE TABLE IF NOT EXISTS invites (
    code        TEXT PRIMARY KEY,
    created_by  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    used_by     TEXT,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id                  TEXT PRIMARY KEY,
    username                   TEXT UNIQUE NOT NULL,
    password_hash              TEXT NOT NULL,
    name                       TEXT,
    race                       TEXT,
    faction                    TEXT,
    backstory                  TEXT,
    inferred_class             TEXT DEFAULT 'Unknown',
    level                      INTEGER NOT NULL DEFAULT 1,
    experience                 INTEGER NOT NULL DEFAULT 0,
    max_hp                     INTEGER NOT NULL DEFAULT 100,
    current_hp                 INTEGER NOT NULL DEFAULT 100,
    max_mp                     INTEGER NOT NULL DEFAULT 50,
    current_mp                 INTEGER NOT NULL DEFAULT 50,
    max_stamina                INTEGER NOT NULL DEFAULT 100,
    current_stamina            INTEGER NOT NULL DEFAULT 100,
    status                     TEXT NOT NULL DEFAULT 'alive',
    secret_objective           TEXT DEFAULT '',
    contribution_score         REAL NOT NULL DEFAULT 0.0,
    byok_key_encrypted         TEXT,
    created_at                 REAL NOT NULL,
    attributes_json            TEXT NOT NULL DEFAULT '{}',
    magic_prof_json            TEXT NOT NULL DEFAULT '{}',
    weapon_prof_json           TEXT NOT NULL DEFAULT '{}',
    milestones_json            TEXT NOT NULL DEFAULT '[]',
    currency_json              TEXT NOT NULL DEFAULT '{"copper":0,"silver":5,"gold":0,"platinum":0}',
    inventory_weight           REAL NOT NULL DEFAULT 0.0,
    weight_capacity            REAL NOT NULL DEFAULT 80.0,
    macros_json                TEXT NOT NULL DEFAULT '[]',
    spell_aliases_json         TEXT NOT NULL DEFAULT '{}',
    backstory_changed_recently INTEGER NOT NULL DEFAULT 0,
    convocation_sent           INTEGER NOT NULL DEFAULT 0,
    languages_json             TEXT NOT NULL DEFAULT '["common_tongue"]'
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    player_id   TEXT NOT NULL REFERENCES players(player_id),
    token_hash  TEXT NOT NULL,
    expires_at  REAL NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    item_id       TEXT PRIMARY KEY,
    player_id     TEXT NOT NULL REFERENCES players(player_id),
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    rarity        TEXT NOT NULL DEFAULT 'common',
    quantity      INTEGER NOT NULL DEFAULT 1,
    equipped      INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conditions (
    condition_id    TEXT PRIMARY KEY,
    player_id       TEXT NOT NULL REFERENCES players(player_id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    duration_turns  INTEGER,
    applied_at_turn INTEGER NOT NULL,
    is_buff         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS history (
    history_id  TEXT PRIMARY KEY,
    turn_number INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id  TEXT PRIMARY KEY,
    turn_start  INTEGER NOT NULL,
    turn_end    INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quest_flags (
    flag_key    TEXT PRIMARY KEY,
    flag_value  TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS character_memory (
    player_id   TEXT PRIMARY KEY REFERENCES players(player_id),
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS world_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS arc_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_images (
    image_id    TEXT PRIMARY KEY,
    prompt      TEXT NOT NULL,
    url         TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS faction_reputation (
    player_id   TEXT NOT NULL REFERENCES players(player_id),
    faction_id  TEXT NOT NULL,
    score       INTEGER NOT NULL DEFAULT 0,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (player_id, faction_id)
);

CREATE TABLE IF NOT EXISTS dice_roll_arguments (
    roll_id              TEXT PRIMARY KEY,
    player_id            TEXT NOT NULL REFERENCES players(player_id),
    roll_type            TEXT NOT NULL,
    dc                   INTEGER NOT NULL,
    description          TEXT NOT NULL,
    initial_roll         INTEGER,
    initial_result       INTEGER,
    argument             TEXT NOT NULL DEFAULT '',
    argument_submitted   INTEGER NOT NULL DEFAULT 0,
    verdict              TEXT,
    circumstance_bonus   INTEGER NOT NULL DEFAULT 0,
    final_result         INTEGER,
    explanation          TEXT NOT NULL DEFAULT '',
    created_at           REAL NOT NULL,
    resolved_at          REAL
);

-- Migration 002: Player resource pools and convocation flag
-- Adds MP, Stamina secondary resources and the isekai convocation tracking flag.

ALTER TABLE players ADD COLUMN convocation_sent    INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN max_mp              INTEGER NOT NULL DEFAULT 50;
ALTER TABLE players ADD COLUMN current_mp          INTEGER NOT NULL DEFAULT 50;
ALTER TABLE players ADD COLUMN max_stamina         INTEGER NOT NULL DEFAULT 100;
ALTER TABLE players ADD COLUMN current_stamina     INTEGER NOT NULL DEFAULT 100;

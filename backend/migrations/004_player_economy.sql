-- Migration 004: Player economy and inventory weight
-- Adds currency wallet, inventory weight tracking, and carry capacity.

ALTER TABLE players ADD COLUMN currency_json      TEXT NOT NULL DEFAULT '{"copper":0,"silver":5,"gold":0,"platinum":0}';
ALTER TABLE players ADD COLUMN inventory_weight   REAL NOT NULL DEFAULT 0.0;
ALTER TABLE players ADD COLUMN weight_capacity    REAL NOT NULL DEFAULT 80.0;

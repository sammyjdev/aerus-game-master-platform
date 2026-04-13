-- Migration 012: Skills proficiency system + point economy + subrace
-- skills_json: organic skill progression per player
--   Format: {"skill_key": {"rank": int, "uses": int, "impact": float}}
--   14 categories, sub-skills grow from use + narrative impact (rank 1-20)
-- attribute_points_available: AP earned 5 per level, 1 AP = +1 to any attribute
-- proficiency_points_available: PP earned 1 per multiple-of-3 level, spent on weapon/magic prof (1-20)
-- subrace: e.g. "human_northerner", "elf_twilight" — determines racial starting attributes

ALTER TABLE players ADD COLUMN skills_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE players ADD COLUMN attribute_points_available INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN proficiency_points_available INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN subrace TEXT;

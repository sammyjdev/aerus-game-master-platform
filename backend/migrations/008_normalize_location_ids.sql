-- Migration 008: Normalize Portuguese location IDs to English
-- current_location is stored as a key-value pair in world_state (not a players column)
UPDATE world_state SET value = 'gorath_fissures'   WHERE key = 'current_location' AND value = 'fendas_de_gorath';
UPDATE world_state SET value = 'ondrek_passage'    WHERE key = 'current_location' AND value = 'passagem_ondrek';
UPDATE world_state SET value = 'ash_heart'         WHERE key = 'current_location' AND value = 'coracao_cinzas';
UPDATE world_state SET value = 'wandering_cities'  WHERE key = 'current_location' AND value = 'urbes_ambulantes';

-- Migration 011: Drop unused summaries table.
-- The summarizer writes to world_memory/arc_memory instead; this table has
-- been inert since memory_manager.py superseded the original design.
DROP TABLE IF EXISTS summaries;

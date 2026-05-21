-- Migration 003: add schema_version column to transactions (Tier 2)
-- Applied manually or via migration runner; idempotent.

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS schema_version TEXT DEFAULT '1.0';

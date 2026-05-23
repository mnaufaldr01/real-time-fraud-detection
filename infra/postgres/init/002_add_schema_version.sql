-- Event schema version on persisted transactions (matches TransactionEvent.schema_version)

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS schema_version TEXT DEFAULT '1.0';

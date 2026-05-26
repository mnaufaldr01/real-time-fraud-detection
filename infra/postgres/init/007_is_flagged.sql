-- Unified flag semantics: any non-approve tier (block, strong_suspect, review)

ALTER TABLE fraud_flags
    ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE fraud_flags
SET is_flagged = is_fraud OR requires_user_confirmation
WHERE is_flagged = FALSE;

CREATE INDEX IF NOT EXISTS idx_fraud_flags_is_flagged
    ON fraud_flags (is_flagged) WHERE is_flagged = TRUE;

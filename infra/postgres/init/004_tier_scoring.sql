-- Multi-tier fraud scoring columns (rules + XGBoost + anomaly)

ALTER TABLE risk_scores
    ADD COLUMN IF NOT EXISTS ml_prob NUMERIC(8, 6);

ALTER TABLE fraud_flags
    ADD COLUMN IF NOT EXISTS risk_tier TEXT,
    ADD COLUMN IF NOT EXISTS requires_user_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ml_prob NUMERIC(8, 6);

CREATE INDEX IF NOT EXISTS idx_transactions_user_timestamp
    ON transactions (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_timestamp
    ON transactions (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_fraud_flags_is_fraud
    ON fraud_flags (is_fraud) WHERE is_fraud = TRUE;

CREATE INDEX IF NOT EXISTS idx_fraud_flags_scored_at
    ON fraud_flags (scored_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_scores_scored_at
    ON risk_scores (scored_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_scores_history_transaction
    ON risk_scores_history (transaction_id);

CREATE INDEX IF NOT EXISTS idx_risk_scores_history_scored_at
    ON risk_scores_history (scored_at DESC);

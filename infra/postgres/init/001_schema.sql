-- Core fraud detection schema

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   UUID PRIMARY KEY,
    user_id          TEXT NOT NULL,
    timestamp        TIMESTAMPTZ NOT NULL,
    amount           NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency         TEXT NOT NULL DEFAULT 'USD',
    merchant_id      TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    country          CHAR(2) NOT NULL,
    payment_method   TEXT NOT NULL CHECK (payment_method IN ('card', 'wallet', 'bank_transfer')),
    device_id        TEXT,
    ip_country       CHAR(2) NOT NULL,
    ingested_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_scores (
    transaction_id   UUID PRIMARY KEY REFERENCES transactions(transaction_id),
    rule_score       NUMERIC(5, 2) NOT NULL CHECK (rule_score BETWEEN 0 AND 100),
    anomaly_score    NUMERIC(5, 2) NOT NULL CHECK (anomaly_score BETWEEN 0 AND 100),
    final_score      NUMERIC(5, 2) NOT NULL CHECK (final_score BETWEEN 0 AND 100),
    ruleset_version  TEXT NOT NULL,
    model_version    TEXT NOT NULL,
    scored_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_flags (
    transaction_id   UUID PRIMARY KEY REFERENCES transactions(transaction_id),
    is_fraud         BOOLEAN NOT NULL,
    flag_reasons     JSONB NOT NULL DEFAULT '[]',
    ruleset_version  TEXT NOT NULL,
    scored_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_scores_history (
    id               BIGSERIAL PRIMARY KEY,
    transaction_id   UUID NOT NULL REFERENCES transactions(transaction_id),
    rule_score       NUMERIC(5, 2) NOT NULL CHECK (rule_score BETWEEN 0 AND 100),
    anomaly_score    NUMERIC(5, 2) NOT NULL CHECK (anomaly_score BETWEEN 0 AND 100),
    final_score      NUMERIC(5, 2) NOT NULL CHECK (final_score BETWEEN 0 AND 100),
    ruleset_version  TEXT NOT NULL,
    model_version    TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    scored_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS batch_runs (
    id               BIGSERIAL PRIMARY KEY,
    dag_run_id       TEXT NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ,
    rows_processed   INTEGER NOT NULL DEFAULT 0,
    ruleset_version  TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    error_message    TEXT
);

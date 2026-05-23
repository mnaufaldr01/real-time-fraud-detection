-- FX rate snapshots (refreshed every 5 minutes by Airflow)

CREATE TABLE IF NOT EXISTS fx_rate_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    as_of         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source        TEXT NOT NULL DEFAULT 'fxratesapi',
    rates         JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fx_snapshots_as_of ON fx_rate_snapshots (as_of DESC);

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS fx_snapshot_id BIGINT REFERENCES fx_rate_snapshots(id),
    ADD COLUMN IF NOT EXISTS fx_as_of TIMESTAMPTZ;

-- Cold-start seed from static fallback rates (USD per 1 unit)
INSERT INTO fx_rate_snapshots (as_of, source, rates)
SELECT NOW(), 'static_seed', '{"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "AUD": 0.65, "SGD": 0.74, "IDR": 0.000063}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM fx_rate_snapshots LIMIT 1);

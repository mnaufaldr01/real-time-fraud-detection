-- Add USD-normalized amount for cross-currency fraud stats (existing deployments)

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS amount_usd NUMERIC(14, 2) NOT NULL DEFAULT 0;

-- Backfill legacy USD-only rows where amount_usd was never set
UPDATE transactions SET amount_usd = amount WHERE amount_usd = 0 AND currency = 'USD';

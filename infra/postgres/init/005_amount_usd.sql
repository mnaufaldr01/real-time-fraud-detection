-- USD-normalized amount for cross-currency fraud stats (idempotent for legacy DBs)

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS amount_usd NUMERIC(14, 2) NOT NULL DEFAULT 0;

UPDATE transactions SET amount_usd = amount WHERE amount_usd = 0 AND currency = 'USD';

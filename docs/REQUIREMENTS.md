# Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | Ingest transactions via Kafka topic `transactions.raw` | Implemented |
| FR-2 | Validate events with Pydantic; invalid → DLQ | Implemented |
| FR-3 | Rule-based scoring (HIGH_AMOUNT, VELOCITY, GEO_MISMATCH, NEW_MERCHANT) | Implemented |
| FR-4 | Anomaly scoring (z-score + optional IsolationForest) | Implemented |
| FR-5 | Multi-signal tier scoring (rules + XGBoost + anomaly) | Implemented |
| FR-6 | Hard-decline rules bypass soft-signal review | Implemented |
| FR-7 | Persist to Postgres (transactions, risk_scores, fraud_flags) | Implemented |
| FR-8 | Idempotent upsert on transaction_id (at-least-once) | Implemented |
| FR-9 | Publish scored events to `transactions.scored` | Implemented |
| FR-10 | Synthetic generator with configurable fraud injection | Implemented |
| FR-11 | FastAPI POST /transactions for manual ingestion | Implemented |
| FR-12 | Airflow batch re-score with stricter ruleset (batch_v2) | Implemented |
| FR-13 | Explainable decisions via flag_reasons JSON + version columns | Implemented |
| FR-14 | XGBoost classifier for bank_transfer (bundled model) | Implemented |
| FR-15 | dbt analytics marts + Streamlit dashboard | Implemented |

## Non-Functional

- Local demo via Docker Compose (Kafka, Postgres, Kafka UI, Airflow)
- p95 latency target: < 2s produce → Postgres (documented, not optimized)
- Delivery semantics: at-least-once + idempotent upsert

See [scoring.md](scoring.md) for tier semantics and [analytics.md](analytics.md) for KPI definitions.

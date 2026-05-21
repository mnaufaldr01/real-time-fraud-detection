# Architecture

## Lambda Architecture

This project implements a simplified lambda architecture:

- **Speed layer (stream):** Kafka consumer scores events in near-real-time with `ruleset_version=stream_v1`
- **Batch layer:** Airflow DAG re-scores historical data with stricter rules (`batch_v2`) into `risk_scores_history`

## Components

| Component | Role |
|-----------|------|
| `producer/generator.py` | Synthetic transaction stream with fraud injection |
| `producer/api/main.py` | FastAPI ingestion endpoint |
| `consumer/main.py` | Stream processing: validate → enrich → score → persist |
| `airflow/dags/daily_rescore.py` | Batch re-scoring with data quality checks |
| `dashboard/app.py` | Streamlit KPIs and flag explorer |

## Data Flow

1. Events published to `transactions.raw` (key = `user_id`)
2. Consumer validates; failures go to `transactions.dlq` with error metadata
3. Valid events enriched with user stats from Postgres
4. Rules + anomaly scores combined; results upserted to Postgres
5. Slim payload published to `transactions.scored`
6. Airflow nightly batch writes to `risk_scores_history` without overwriting stream scores

## Kafka Client

Uses `confluent-kafka` (production-aligned Python client).

## Delivery Semantics

At-least-once delivery with idempotent `ON CONFLICT` upserts on `transaction_id`.

## Future (Tier 3)

See README Tier 3 section — Confluent Cloud, Snowflake, Spark Structured Streaming.

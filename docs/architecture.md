# Architecture

## Lambda architecture

- **Speed layer (stream):** Kafka consumer scores events in near-real-time with `ruleset_version=stream_v1` and multi-signal tier assignment
- **Batch layer:** Airflow DAG re-scores historical data with stricter rules (`batch_v2`) into `risk_scores_history`

Scoring details: [scoring.md](scoring.md)

## Components

| Component | Role |
| --------- | ---- |
| `producer/generator.py` | Synthetic transaction stream with fraud injection |
| `producer/api/main.py` | FastAPI ingestion + cascade delete |
| `consumer/main.py` | Validate → FX → rules + XGBoost + anomaly → persist |
| `airflow/dags/daily_rescore.py` | Batch re-scoring with data quality checks |
| `airflow/dags/model_retrain_weekly.py` | Safe deployment: static-data retrain, promote if improved |
| `airflow/dags/dbt_marts_refresh.py` | Scheduled `dbt run` |
| `analytics_api/main.py` | FastAPI JSON API over dbt marts |
| `frontend/` | React analytics dashboard — [README](../frontend/README.md) |

## Data flow

1. Events published to `transactions.raw` (key = `user_id`)
2. Consumer validates; failures → `transactions.dlq`
3. FX snapshot loaded; `amount_usd` computed
4. Rules, XGBoost (bank transfer), and anomaly scored; multi-signal tier assigned
5. Upsert to `transactions`, `risk_scores`, `fraud_flags` (`is_fraud`, `is_flagged`, `risk_tier`)
6. Slim payload → `transactions.scored`
7. Airflow batch writes `risk_scores_history` without overwriting stream scores
8. dbt builds marts; React dashboard (via analytics API) reads `analytics.*`

## Kafka client

Uses **confluent-kafka**. Single-broker Compose with Zookeeper for local dev.

## Postgres schemas

| Schema / table | Purpose |
| -------------- | ------- |
| `public.transactions` | Core events + USD amounts |
| `public.fraud_flags` | Tier, flags, `flag_reasons` |
| `public.risk_scores` | Stream scores |
| `public.risk_scores_history` | Batch scores |
| `analytics.*` | dbt marts |

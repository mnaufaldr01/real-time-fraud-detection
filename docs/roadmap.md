# Roadmap

Planned extensions beyond the current local Docker stack. **Current system overview:** [project README](../README.md#architecture) · **All docs:** [index.md](index.md). The pipeline today keeps **OLTP in PostgreSQL**, **analytics in dbt marts on the same database**, and **weekly retrain on static PaySim/synthetic data** — see [architecture.md](architecture.md) and [ml_retrain.md](ml_retrain.md).

## Priority themes

| # | Theme | Summary |
| - | ----- | ------- |
| 1 | [Warehouse-backed analytics](#1-warehouse-backed-analytics) | Move heavy history and marts to Snowflake, Databricks, or ClickHouse |
| 2 | [Cloud deployment](#2-cloud-native-deployment--iac--cicd) | Managed Kafka, Postgres, Airflow, containers, IaC, CI/CD |
| 3 | [Downstream on `transactions.scored`](#3-downstream-actions-on-transactionsscored) | Act on decisions in near real time |
| 4 | [Streaming hardening](#4-dlq-replay--schema-registry) | DLQ replay and schema registry |
| 5 | [Label loop + warehouse retrain](#5-label-feedback-loop--warehouse-retrain) | Production learning from vetted labels |
| 6 | [Observability](#6-observability) | Metrics, alerts, drift |
| 7 | [Feature store + online inference](#7-feature-store--online-inference) | Decouple features and model serving from the consumer |
| 8 | [Case management](#8-case-management-for-review-tier) | Analyst queue for `review` tier |

---

## 1. Warehouse-backed analytics

**Goal:** Scale analytics without overloading Postgres OLTP.

- Run **dbt** against **Snowflake** or **Databricks** (lakehouse / Delta) for historical marts, stream-vs-batch comparisons, and dashboard KPIs at large volume.
- Ingest **Kafka** (`transactions.scored` or raw) into **ClickHouse** for real-time aggregates (velocity, country rates, tier mix).
- Split **hot** (recent operational data in Postgres) vs **cold** (years of events in the warehouse).
- Use warehouse-native pre-aggregations or materializations where the React dashboard needs sub-second reads.

**Touches:** `dbt_fraud/`, `analytics_api/`, Airflow `dbt_marts_refresh`, [analytics.md](analytics.md).

---

## 2. Cloud-native deployment + IaC + CI/CD

**Goal:** Repeatable dev/staging/prod outside a single Compose host.

- **Managed Kafka** (MSK, Confluent Cloud) and **managed Postgres** (RDS, Aurora, Cloud SQL).
- Run consumer, ingestion API, and analytics API on **ECS/EKS** (or equivalent) with autoscaling.
- **Managed Airflow** (MWAA, Astronomer) or orchestrate via Databricks Workflows where appropriate.
- **Terraform / Pulumi** for infrastructure; secrets in a cloud secret manager (not `.env` in prod).
- **CI/CD:** build images, run `pytest` + `ruff`, deploy DAGs, dbt, and promoted model bundles on merge.

**Touches:** `docker-compose.yml`, `.github/workflows/`, [setup.md](setup.md).

---

## 3. Downstream actions on `transactions.scored`

**Goal:** Use the scored Kafka topic for operational workflows (today nothing subscribes).

- Consumers for **payment hold/release**, customer notification, or internal audit bus.
- Optional **fraud ops** feed: live stream of `block`, `strong_suspect`, and `review` outcomes.
- Keep Postgres as system of record; Kafka for low-latency fan-out (see [architecture.md](architecture.md)).

**Touches:** `consumer/sink.py` (`transactions.scored` payload), new service(s) in `producer/` or a dedicated `integrations/` package.

---

## 4. DLQ replay + schema registry

**Goal:** Production-grade streaming ergonomics.

- **DLQ replay:** Tooling or DAG to reprocess `transactions.dlq` after fixes (schema, FX, bugs); metrics on DLQ rate.
- **Schema registry:** Avro/Protobuf + compatibility rules instead of ad hoc JSON only; align with [event_schema.json](event_schema.json).
- Document delivery semantics (at-least-once + idempotent upsert today) vs future transactional outbox if exactly-once side effects are required.

**Touches:** `consumer/main.py`, `consumer/validate.py`, Kafka topic setup in `docker-compose.yml`.

---

## 5. Label feedback loop + warehouse retrain

**Goal:** Learn from confirmed fraud and vetted negatives, not stream `is_fraud` alone.

- Extract labeled rows from the warehouse (analyst-confirmed fraud + verified negatives).
- Undersample majority class; optional hyperparameter tuning; **time-based holdout**; promote only when metrics beat production.
- Extends the idea in [ml_retrain.md § Future enhancement](ml_retrain.md#future-enhancement) — current `model_retrain_weekly` stays on static PaySim/synthetic data by design.

**Touches:** `shared/model_retrain.py`, `airflow/dags/model_retrain_weekly.py`, `fraud_flags` / case outcomes, theme **8** below.

---

## 6. Observability

**Goal:** Operate the pipeline with SLOs, not only logs and Airflow DQ.

- **Metrics:** Consumer latency (p95 produce → Postgres), scoring throughput, DLQ volume, FX snapshot age, fraud-rate bands.
- **Tracing:** OpenTelemetry across ingest API → Kafka → consumer → Postgres.
- **Alerting:** DLQ spikes, stale FX, `daily_rescore` mismatch %, model bundle load failures.
- **ML monitoring:** Score distribution drift, delayed-label precision/recall where labels exist.

**Touches:** `consumer/main.py` (structured JSON logs today), `airflow/dags/daily_rescore.py` (data quality checks).

---

## 7. Feature store + online inference

**Goal:** Consistent features and serving at scale, separate from the consumer process.

- **Feature store** (e.g. Feast): rolling velocity, amount percentiles, merchant history — shared by stream and batch paths.
- **Online inference:** Dedicated model service (MLflow, SageMaker, BentoML) instead of in-process joblib in the consumer.
- **Champion/challenger:** Shadow scoring before promoting new bundles; ties to [ml_retrain.md](ml_retrain.md).
- Expand ML beyond **bank_transfer** where product allows ([scoring.md](scoring.md)).

**Touches:** `consumer/`, `models/`, `FraudSink.load_user_stats`, rules and anomaly feature builders.

---

## 8. Case management for `review` tier

**Goal:** Close the loop from detection to human decision.

- Queue for transactions with `requires_user_confirmation` (`review` tier in [scoring.md](scoring.md)).
- Analyst actions: confirm fraud, clear false positive, add notes.
- Feed outcomes into theme **5** (warehouse labels) for retrain and reporting.

**Touches:** `fraud_flags`, new API/UI (or extend `frontend/`), Postgres audit tables.

---

## Suggested phasing

| Horizon | Focus |
| ------- | ----- |
| **Near term** | Cloud MVP (managed Kafka + Postgres + containerized consumer/API), basic CI/CD, metrics on consumer and DLQ |
| **Medium term** | Warehouse + dbt move, subscriber on `transactions.scored`, DLQ replay, case management MVP |
| **Long term** | Feature store, production learning loop (theme 5), online inference, multi-region and DR |

---

## Related docs

| Doc | Link |
| --- | ---- |
| Architecture (current) | [architecture.md](architecture.md) |
| Model retrain (current + ML future note) | [ml_retrain.md](ml_retrain.md) |
| Scoring tiers | [scoring.md](scoring.md) |
| Requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |

# Real-Time Fraud Detection

A real-time fraud detection pipeline: synthetic transactions (PaySim-inspired) flow through **Kafka**, get scored by a stream consumer (**rules + XGBoost + IsolationForest**), persist to **PostgreSQL**, are re-scored nightly by **Airflow** with a stricter batch ruleset, and feed a **Streamlit** dashboard via **dbt** analytics marts.

```mermaid
flowchart LR
  subgraph ingest [Ingestion]
    Gen[transaction_generator]
    API[FastAPI_ingestion]
    PaySim[paysim_replay]
  end
  subgraph kafka [Kafka]
    Raw[transactions.raw]
    DLQ[transactions.dlq]
    Scored[transactions.scored]
  end
  subgraph stream [Stream_processing]
    Consumer[fraud_consumer]
    Rules[rules_engine]
    XGB[XGBoost_classifier]
    IF[IsolationForest]
  end
  subgraph store [PostgreSQL]
    Txn[transactions]
    Risk[risk_scores]
    Flags[fraud_flags]
    Hist[risk_scores_history]
    Runs[batch_runs]
    FX[fx_rate_snapshots]
  end
  subgraph batch [Airflow]
    Rescore[daily_rescore]
    Retrain[model_retrain_weekly]
    FxDAG[fx_rate_refresh]
    DbtRefresh[dbt_marts_refresh]
  end
  subgraph analytics [dbt_analytics]
    dbt[dbt_fraud_marts]
  end
  subgraph ui [Dashboard]
    Dash[Streamlit_dashboard]
  end
  Gen --> Raw
  API --> Raw
  PaySim --> Raw
  Raw --> Consumer
  Consumer -->|invalid| DLQ
  Consumer --> Rules
  Consumer --> XGB
  Consumer --> IF
  Consumer --> Scored
  Consumer --> Txn
  Consumer --> Risk
  Consumer --> Flags
  FxDAG --> FX
  FX --> Consumer
  Rescore --> Txn
  Rescore --> Hist
  Rescore --> Runs
  DbtRefresh --> dbt
  Txn --> dbt
  Flags --> dbt
  Risk --> dbt
  Hist --> dbt
  dbt --> Dash
```

## Lambda layers

| Layer | Component | Version | Purpose |
| ----- | --------- | ------- | ------- |
| Speed | Kafka consumer | `stream_v1` | Multi-signal tier scoring |
| ML | XGBoost | bundled | Fraud probability for `bank_transfer` |
| Anomaly | IsolationForest | `anomaly_v1` | Unsupervised outlier score |
| Batch | Airflow | `batch_v2` | Stricter re-score → history |
| ML ops | Airflow | weekly | Safe redeploy: retrain static data → promote only if better |
| FX | Airflow | — | FX snapshots every 5 min |
| Analytics | dbt | `fraud_analytics` | Staging → marts in `analytics` schema |

## Quick start

```powershell
copy .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1
python scripts/train_anomaly.py
python -m consumer.main          # terminal 1
python -m producer.generator     # terminal 2
```

Full setup, service URLs, and env vars: **[docs/setup.md](docs/setup.md)**

## Documentation

| Topic | Doc |
| ----- | --- |
| Setup & commands | [docs/setup.md](docs/setup.md) |
| Scoring & tiers | [docs/scoring.md](docs/scoring.md) |
| dbt & dashboard KPIs | [docs/analytics.md](docs/analytics.md) |
| Python dependencies | [docs/dependencies.md](docs/dependencies.md) |
| Demo walkthrough | [docs/demo.md](docs/demo.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Model retrain (MLOps) | [docs/ml_retrain.md](docs/ml_retrain.md) |

## Model retrain (`model_retrain_weekly`)

The weekly Airflow DAG is for **safe deployment**, not learning from live fraud patterns. It retrains on the same static sources as offline training (PaySim CSV or feature cache for the classifier; synthetic data for the anomaly model), writes candidates to `models/staging/`, compares holdout metrics to the current production bundles, and **promotes only if the candidate is better** (or if no production model exists). Use it to recover missing `models/*.joblib` files, ship training-pipeline or hyperparameter changes, or rehearse a champion/challenger promote flow. Restart the fraud consumer after promotion so joblib bundles reload. Details: [docs/ml_retrain.md](docs/ml_retrain.md).

**Future enhancement (not implemented):** production-aware retraining from Postgres — e.g. pull confirmed-fraud and clean negative labels over a rolling window, undersample negatives to balance classes, tune on that mix (or PaySim + production), and promote with time-based evaluation. That would replace self-labeled `is_fraud` stream scores with operational ground truth and is the path toward industry-style continuous learning.

## Scoring (summary)

Multi-signal cascade: hard decline → auto-decline (ML high / rules ≥ 85) → review (2+ soft signals) → approve. See **[docs/scoring.md](docs/scoring.md)** for thresholds, flag reasons, and examples.

## Project structure

```
producer/          # Generator, FastAPI, PaySim replay
consumer/          # Stream scoring: validate → FX → rules + ML + anomaly
airflow/dags/      # daily_rescore, model_retrain_weekly, fx_rate_refresh, dbt_marts_refresh
dashboard/         # Streamlit KPIs
dbt_fraud/         # Analytics marts
infra/postgres/    # Schema migrations
analysis/          # PaySim training helpers, profiling
models/            # Classifier + anomaly bundles
scripts/           # Train models, seed users, wait-for
shared/            # Schema, FX, synthetic data
tests/             # Unit tests
docs/              # Detailed documentation
```

## Testing

```powershell
pytest tests/unit -v
ruff check .
```

## Delivery semantics

At-least-once Kafka delivery with idempotent `INSERT ... ON CONFLICT` upserts on `transaction_id`.

## License

MIT

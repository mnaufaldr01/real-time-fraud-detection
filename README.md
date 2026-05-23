# Real-Time Fraud Detection

A portfolio-grade real-time fraud detection pipeline: synthetic transactions flow through **Kafka**, get scored by a stream consumer (rules + anomaly detection), persist to **PostgreSQL**, and are re-scored nightly by **Airflow** with a stricter batch ruleset.

```mermaid
flowchart LR
  subgraph ingest [Ingestion]
    Gen[transaction_generator]
    API[FastAPI_ingestion]
  end
  subgraph kafka [Kafka]
    Raw[transactions.raw]
    DLQ[transactions.dlq]
    Scored[transactions.scored]
  end
  subgraph stream [Stream_processing]
    Consumer[fraud_consumer]
  end
  subgraph store [PostgreSQL]
    Txn[transactions]
    Risk[risk_scores]
    Flags[fraud_flags]
    Hist[risk_scores_history]
    Runs[batch_runs]
  end
  subgraph batch [Airflow]
    DAG[daily_rescore_dag]
  end
  subgraph ui [Dashboard]
    Dash[Streamlit_dashboard]
  end
  Gen --> Raw
  API --> Raw
  Raw --> Consumer
  Consumer -->|invalid| DLQ
  Consumer --> Scored
  Consumer --> Txn
  Consumer --> Risk
  Consumer --> Flags
  DAG --> Txn
  DAG --> Hist
  DAG --> Risk
  DAG --> Runs
  Txn --> Dash
  Flags --> Dash
```

## Lambda Story

| Layer | Component | Version tag | Purpose |
|-------|-----------|-------------|---------|
| Speed | Kafka consumer | `stream_v1` | Low-latency scoring |
| Batch | Airflow DAG | `batch_v2` | Stricter re-score into history table |

## Prerequisites

- Docker Desktop (8 GB+ RAM recommended)
- Python 3.11+ (use **3.12** for both venvs when possible)
- Make (optional; PowerShell commands provided below)

### Two virtual environments (recommended)

| Venv | File | Python | Purpose |
|------|------|--------|---------|
| `.venv` | `requirements.txt` | **3.11+** | Pipeline, API, consumer, tests (`-e .[...]` editable install) |
| `.venv-analysis` | `requirements-analysis.txt` | 3.11+ | EDA notebook only (pandas, matplotlib, seaborn; **no** `-e .` install) |

If `pip install -r requirements.txt` fails with `requires a different Python: 3.10.x not in '>=3.11'`, recreate `.venv` with `py -3.12 -m venv .venv`, or use `.venv-analysis` for notebooks only.

```powershell
# Analysis / Jupyter (lighter deps, no editable package)
py -3.12 -m venv .venv-analysis
.\.venv-analysis\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-analysis.txt
python -m ipykernel install --user --name=fraud-analysis --display-name "Fraud Detection (analysis)"
```

In Cursor/VS Code, select the **Fraud Detection (analysis)** kernel for `analysis/EDA.ipynb`.

## Quick Start

```powershell
# 1. Copy env, create pipeline venv, and install Python deps
copy .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. Start infrastructure
docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1

# 3. Train anomaly model (optional but recommended)
python scripts/train_anomaly.py

# 4. Start consumer (terminal 1)
python -m consumer.main

# 5. Start generator (terminal 2)
python -m producer.generator
```

### Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Kafka UI | http://localhost:8080 | — |
| Airflow | http://localhost:8081 | admin / admin |
| FastAPI | http://localhost:8000/docs | — |
| Streamlit | http://localhost:8501 | — |

## Multi-currency model

Events carry **local `amount` + `currency`** on Kafka (USD, GBP, AUD, SGD, IDR, EUR). FX conversion for fraud detection runs **only in the consumer** after schema validation:

1. Validate `TransactionEvent`
2. Load latest FX snapshot from `fx_rate_snapshots` (refreshed every **5 minutes** by the Airflow `fx_rate_refresh` DAG via [fxratesapi.com](https://api.fxratesapi.com))
3. `amount_usd = to_usd(amount, currency, rates=snapshot.rates)` — see [`shared/fx.py`](shared/fx.py) and [`shared/fx_provider.py`](shared/fx_provider.py)
4. Rules and anomaly scoring use **USD**; Postgres stores `amount`, `currency`, `amount_usd`, `fx_snapshot_id`, and `fx_as_of`

Set `FX_API_KEY` in `.env` for the Airflow DAG. The consumer reads Postgres only (no direct API calls). If no snapshot exists yet, static fallback rates in `shared/fx.py` are used.

Publishers (generator, PaySim replay, seed) still use static fallback rates to fabricate local denominations; only the consumer uses live snapshots.

```powershell
python -m producer.paysim_replay --limit 1000          # smoke test
python -m producer.paysim_replay --sample-rate 0.01    # 1% subsample
make replay-paysim
```

## Demo Script (5 steps)

### Step 1 — Bring up infrastructure

```powershell
docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1
```

### Step 2 — Start generator + consumer

```powershell
# Terminal 1
python -m consumer.main

# Terminal 2
python -m producer.generator
```

Watch Kafka UI at http://localhost:8080 — messages on `transactions.raw` and `transactions.scored`.

### Step 3 — POST a fraudulent payload

```powershell
# Start API if not running
uvicorn producer.api.main:app --port 8000

# Geo mismatch fraud
curl -X POST http://localhost:8000/transactions `
  -H "Content-Type: application/json" `
  -d '{"transaction_id":"11111111-1111-1111-1111-111111111111","user_id":"demo_user","timestamp":"2026-05-21T12:00:00Z","amount":999.99,"currency":"USD","merchant_id":"m_fraud","merchant_category":"7995","country":"US","payment_method":"card","ip_country":"RU"}'
```

### Step 4 — Query Postgres for flag_reasons

```powershell
docker exec -it real-time-fraud-detection-postgres-1 psql -U fraud -d fraud_db -c `
  "SELECT transaction_id, is_fraud, flag_reasons, final_score FROM fraud_flags ff JOIN risk_scores rs ON rs.transaction_id = ff.transaction_id WHERE ff.is_fraud ORDER BY ff.scored_at DESC LIMIT 5;"
```

### Step 5 — Trigger Airflow batch re-score

1. Open http://localhost:8081 (admin/admin)
2. Enable and trigger the `daily_rescore` DAG
3. Compare stream vs batch:

```sql
SELECT rs.final_score AS stream_score, rsh.final_score AS batch_score
FROM risk_scores rs
JOIN risk_scores_history rsh ON rsh.transaction_id = rs.transaction_id
LIMIT 10;
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make up` | Start Docker services + wait |
| `make down` | Tear down volumes |
| `make consumer` | Run stream consumer |
| `make generator` | Run synthetic producer |
| `make api` | Run FastAPI ingestion |
| `make dashboard` | Run Streamlit dashboard |
| `make test` | Run unit tests |
| `make train-model` | Train IsolationForest |
| `make profile` | Generate data profile markdown |

## Scoring Rules

| Rule | Trigger | Weight |
|------|---------|--------|
| HIGH_AMOUNT | amount > user P99 (or global P99) | 40 |
| VELOCITY_1H | > 5 tx/user/hour (3 in batch) | 35 |
| GEO_MISMATCH | country ≠ ip_country | 50 (hard decline) |
| NEW_MERCHANT_HIGH | first merchant + amount > P95 | 30 |

**Final score:** `0.6 × rule_score + 0.4 × anomaly_score` — flagged when ≥ 70 or hard-decline rule fires.

## Delivery Semantics

At-least-once Kafka delivery with idempotent `INSERT ... ON CONFLICT` upserts on `transaction_id`.

## Kafka Client

Uses **confluent-kafka** (production-aligned). Single-broker Compose with Zookeeper for cross-platform simplicity; KRaft migration noted as future ops improvement.

## Project Structure

```
producer/     # Generator + FastAPI ingestion
consumer/     # Stream scoring pipeline
airflow/      # Batch re-score DAG
dashboard/    # Streamlit KPIs
infra/        # Postgres schema + migrations
analysis/     # Data profiling script
scripts/      # Train model, seed users, wait-for
tests/        # Unit tests
docs/         # Requirements, schema, architecture
```

## Testing

```powershell
pytest tests/unit -v
ruff check .
```

CI runs lint + unit tests on push (`.github/workflows/ci.yml`).

## Tier 3 — Future Work (not implemented)

- **Kafka:** Migrate to Confluent Cloud with Schema Registry
- **Warehouse:** Export Postgres analytics to Snowflake
- **Stream processing:** Secondary consumer in Spark Structured Streaming
- **Ops:** KRaft mode, exactly-once semantics, auth, multi-region

## License

MIT

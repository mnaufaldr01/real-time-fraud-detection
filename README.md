# Real-Time Fraud Detection

A real-time fraud detection pipeline: synthetic transactions (based on PaySim dataset) flow through **Kafka**, get scored by a stream consumer (**rules + XGBoost + IsolationForest anomaly**), persist to **PostgreSQL**, and are re-scored nightly by **Airflow** with a stricter batch ruleset.

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
    FxDAG[fx_rate_refresh]
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
  Txn --> Dash
  Flags --> Dash
```



## Lambda Story


| Layer   | Component          | Version tag              | Purpose                                              |
| ------- | ------------------ | ------------------------ | ---------------------------------------------------- |
| Speed   | Kafka consumer     | `stream_v1`              | Low-latency multi-tier scoring                       |
| ML      | XGBoost classifier | `ml_v1_static` (bundled) | PaySim-trained fraud probability for `bank_transfer` |
| Anomaly | IsolationForest    | `anomaly_v1`             | Unsupervised outlier score                           |
| Batch   | Airflow DAG        | `batch_v2`               | Stricter re-score into history table                 |
| FX      | Airflow DAG        | —                        | Live FX snapshots every 5 minutes                    |


## Prerequisites

- Docker Desktop (8 GB+ RAM recommended)
- Python 3.11+ (use **3.12** for both venvs when possible)
- Make (optional; PowerShell commands provided below)

### Two virtual environments (recommended)


| Venv             | File                        | Python    | Purpose                                                                        |
| ---------------- | --------------------------- | --------- | ------------------------------------------------------------------------------ |
| `.venv`          | `requirements.txt`          | **3.11+** | Pipeline, API, consumer, tests (`-e .[...]` editable install)                  |
| `.venv-analysis` | `requirements-analysis.txt` | 3.11+     | PaySim model training, EDA notebooks (includes **XGBoost**; no `-e .` install) |


If `pip install -r requirements.txt` fails with `requires a different Python: 3.10.x not in '>=3.11'`, recreate `.venv` with `py -3.12 -m venv .venv`, or use `.venv-analysis` for notebooks only.

```powershell
# Analysis / Jupyter (PaySim training + EDA)
py -3.12 -m venv .venv-analysis
.\.venv-analysis\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-analysis.txt
python -m ipykernel install --user --name=fraud-analysis --display-name "Fraud Detection (analysis)"
```

In Cursor/VS Code, select the **Fraud Detection (analysis)** kernel for `models/model-training.ipynb` and `analysis/EDA.ipynb`.

## Quick Start

```powershell
# 1. Copy env, create pipeline venv, and install Python deps
copy .env.example .env
# Docker maps Postgres to host port 5433 — update DATABASE_URL in .env:
# DATABASE_URL=postgresql://fraud:fraud@localhost:5433/fraud_db

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install xgboost   # required for XGBoost classifier inference in the consumer

# 2. Start infrastructure
docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1

# 3. Models (pre-trained classifier bundled; train anomaly if missing)
python scripts/train_anomaly.py
# Optional: retrain classifier from PaySim CSV (uses .venv-analysis + xgboost)
# python scripts/train_fraud_classifier.py

# 4. Start consumer (terminal 1)
python -m consumer.main

# 5. Start generator (terminal 2)
python -m producer.generator
```

### Service URLs


| Service           | URL                                                      | Credentials   |
| ----------------- | -------------------------------------------------------- | ------------- |
| Kafka UI          | [http://localhost:8080](http://localhost:8080)           | —             |
| Airflow           | [http://localhost:8081](http://localhost:8081)           | admin / admin |
| FastAPI           | [http://localhost:8000/docs](http://localhost:8000/docs) | —             |
| Streamlit         | [http://localhost:8501](http://localhost:8501)           | —             |
| PostgreSQL (host) | localhost:**5433**                                       | fraud / fraud |


## Multi-currency model

Events carry **local `amount` + `currency`** on Kafka (USD, GBP, AUD, SGD, IDR, EUR). FX conversion for fraud detection runs **only in the consumer** after schema validation:

1. Validate `TransactionEvent`
2. Load latest FX snapshot from `fx_rate_snapshots` (refreshed every **5 minutes** by the Airflow `fx_rate_refresh` DAG via [fxratesapi.com](https://api.fxratesapi.com))
3. `amount_usd = to_usd(amount, currency, rates=snapshot.rates)` — see `[shared/fx.py](shared/fx.py)` and `[shared/fx_provider.py](shared/fx_provider.py)`
4. Rules, XGBoost, and anomaly scoring use **USD**; Postgres stores `amount`, `currency`, `amount_usd`, `fx_snapshot_id`, and `fx_as_of`

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

Watch Kafka UI at [http://localhost:8080](http://localhost:8080) — messages on `transactions.raw` and `transactions.scored`.

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
  "SELECT transaction_id, risk_tier, is_fraud, flag_reasons, ml_prob, final_score FROM fraud_flags ff JOIN risk_scores rs ON rs.transaction_id = ff.transaction_id WHERE ff.is_fraud ORDER BY ff.scored_at DESC LIMIT 5;"
```

### Step 5 — Trigger Airflow batch re-score

1. Open [http://localhost:8081](http://localhost:8081) (admin/admin)
2. Enable and trigger `**fx_rate_refresh**` (needs `FX_API_KEY`) and `**daily_rescore**`
3. Compare stream vs batch:

```sql
SELECT rs.final_score AS stream_score, rsh.final_score AS batch_score
FROM risk_scores rs
JOIN risk_scores_history rsh ON rsh.transaction_id = rs.transaction_id
LIMIT 10;
```

## Makefile Targets


| Target               | Description                          |
| -------------------- | ------------------------------------ |
| `make up`            | Start Docker services + wait         |
| `make down`          | Tear down volumes                    |
| `make wait`          | Wait for core services               |
| `make consumer`      | Run stream consumer                  |
| `make generator`     | Run synthetic producer               |
| `make replay-paysim` | Replay PaySim CSV to Kafka           |
| `make api`           | Run FastAPI ingestion                |
| `make dashboard`     | Run Streamlit dashboard              |
| `make test`          | Run unit tests                       |
| `make train-model`   | Train IsolationForest (`anomaly_v1`) |
| `make seed`          | Seed user history in Postgres        |
| `make profile`       | Generate data profile markdown       |
| `make demo`          | Start infra + print demo steps       |


Train the supervised classifier separately:

```powershell
python scripts/train_fraud_classifier.py   # writes models/fraud_classifier_v1.joblib
```

## Scoring Pipeline

After FX conversion, each valid event passes through three scorers — **rules**, **XGBoost**, and **anomaly** — then a **tier cascade** picks the outcome. The cascade is evaluated top-down; the first matching condition wins.

```
hard-decline rules?  →  block
ML prob ≥ t_high?    →  strong_suspect   (bank_transfer only)
ML prob ≥ t_low?     →  review           (bank_transfer only)
rule_score ≥ 50?     →  review
anomaly_score ≥ 70?  →  review
not bank_transfer?   →  out_of_scope
else                 →  approve
```

| Tier | Name             | `is_fraud` | User confirmation                                       |
| ---- | ---------------- | ---------- | ------------------------------------------------------- |
| 0    | `out_of_scope`   | No         | No — card/wallet skip XGBoost                           |
| 1    | `block`          | Yes        | No — hard-decline rules                                 |
| 2    | `strong_suspect` | Yes        | No — ML prob ≥ `threshold_high`                         |
| 3    | `review`         | No         | Yes — soft rules, anomaly, or ML prob ≥ `threshold_low` |
| 4    | `approve`        | No         | No                                                      |

Persisted `flag_reasons` (JSON array on `fraud_flags`) explain **why** the tier was chosen. A transaction can carry multiple reasons — e.g. `["GEO_MISMATCH", "HARD_DECLINE"]` when geo mismatch triggers an immediate block.

### Rulesets: `stream_v1` vs `batch_v2`

Both rulesets evaluate the same four rules with identical weights. They differ in **thresholds** and **where they run**:

| | Stream (`stream_v1`) | Batch (`batch_v2`) |
| --- | --- | --- |
| **Runs in** | Kafka consumer (real-time) | Airflow `daily_rescore` DAG |
| **Velocity limit** | > 5 tx/user/hour | > 3 tx/user/hour |
| **Amount P99 fallback** | Global $850 (or user 30-day P99) | Global × 0.85 (or user P99 × 0.85) |
| **Amount P95 fallback** | Global $450 (or user 30-day P95) | Global × 0.85 (or user P95 × 0.85) |
| **Output table** | `risk_scores` + `fraud_flags` | `risk_scores_history` |

**How `rule_score` is computed:** each triggered rule adds its weight; the sum is capped at 100. Multiple rules can fire on one transaction (e.g. high amount + geo mismatch → score 90).

**User context loaded from Postgres** (per event):

- `tx_count_1h` — transactions for this user in the rolling hour before the event timestamp
- `amount_p99` / `amount_p95` — user percentiles over the last 30 days (USD); falls back to global defaults when no history
- `seen_merchants` — distinct merchants this user has transacted with before

Override defaults via `.env`: `VELOCITY_1H_LIMIT`, `GLOBAL_AMOUNT_P95`, `GLOBAL_AMOUNT_P99`, `RULE_REVIEW_THRESHOLD` (default 50).

### Rules reference

| Rule | Weight | Hard decline | What it detects |
| ---- | ------ | ------------ | --------------- |
| `HIGH_AMOUNT` | 40 | No | Transaction exceeds the user's normal spending. Fires when `amount_usd` is above the user's 30-day 99th percentile; new users use the global P99 ($850 stream / ~$723 batch). Catches sudden large purchases or account takeover spend-down. |
| `VELOCITY_1H` | 35 | **Yes** | Too many transactions in a short window — classic card-testing or burst fraud. Fires when the user has more than 5 tx in the prior hour (stream) or 3 (batch). Counts existing Postgres rows, so synthetic velocity fraud needs prior txs in the window. |
| `GEO_MISMATCH` | 50 | **Yes** | Billing country differs from IP geolocation. Fires when `country ≠ ip_country` (e.g. card registered in US, IP in RU). Strong signal for stolen credentials or VPN/proxy abuse. |
| `NEW_MERCHANT_HIGH` | 30 | No | First purchase at an unseen merchant for a large amount. Fires when `merchant_id` is new to the user **and** `amount_usd` exceeds the user's P95 (or global $450 / ~$383 batch). Catches mule payouts or first-time high-value merchant fraud. |

**Hard decline:** if `GEO_MISMATCH` or `VELOCITY_1H` fires, the transaction is immediately tier `block` regardless of ML or anomaly scores. The synthetic generator injects these patterns deliberately (`geo_mismatch`, `velocity`, `high_amount`).

### ML classifier (XGBoost)

- Trained on PaySim **TRANSFER / CASH_OUT** → scoped to `payment_method=bank_transfer`
- Pre-trained bundle: `models/fraud_classifier_v1.joblib` (thresholds loaded from bundle)
- Training pipeline: `analysis/paysim_training.py` + `scripts/train_fraud_classifier.py` or `models/model-training.ipynb`
- Without the bundle or `xgboost` installed, the consumer falls back to rules + anomaly only
- Thresholds (`threshold_low`, `threshold_high`) come from the training bundle; env fallbacks: `ML_THRESHOLD_LOW` (0.03), `ML_THRESHOLD_HIGH` (0.22)

### Anomaly score

Combines two signals (takes the **max**):

1. **Z-score** — how far `amount_usd` deviates from the user's 30-day mean/std (global fallback when no history); mapped to 0–100 (z ≥ 4 → 100)
2. **IsolationForest** — unsupervised model on `[amount_usd, hour_of_day, merchant_category]` (`models/anomaly_v1.joblib`); omitted if model file missing

An anomaly score ≥ 70 (`ANOMALY_REVIEW_THRESHOLD`) routes to tier `review` unless a higher-priority condition already matched.

### Final score

`final_score = max(rule_score, anomaly_score, ml_prob × 100)` — used for dashboards and batch comparison; **tier assignment** (not `final_score` alone) drives `is_fraud` and `requires_user_confirmation`.

### Flag reasons reference

`flag_reasons` is the audit trail stored on each scored transaction. Values fall into two groups: **rule hits** (which rules fired) and **tier drivers** (why that tier was chosen).

#### Rule hits

These appear whenever the corresponding rule triggers. They can coexist with tier-driver reasons.

| Reason | Source | Meaning |
| ------ | ------ | ------- |
| `HIGH_AMOUNT` | Rules engine | `amount_usd` exceeded the user's P99 (or global fallback). Contributes +40 to `rule_score`. Alone it usually lands in `approve` unless combined with other signals; at +40 it stays below the 50-point review threshold. |
| `VELOCITY_1H` | Rules engine | User exceeded the hourly transaction count. Contributes +35 and triggers **hard decline** → tier `block` with `HARD_DECLINE` also appended. |
| `GEO_MISMATCH` | Rules engine | `country` and `ip_country` differ. Contributes +50 and triggers **hard decline** → tier `block`. |
| `NEW_MERCHANT_HIGH` | Rules engine | First-time merchant for this user with amount above P95. Contributes +30. Soft rule — does not hard-decline on its own. |

#### Tier drivers

These are appended by the tier cascade to explain the **decision**, not just which rules fired.

| Reason | Tier | Meaning |
| ------ | ---- | ------- |
| `HARD_DECLINE` | `block` | A hard-decline rule (`GEO_MISMATCH` or `VELOCITY_1H`) fired. Transaction is treated as fraud (`is_fraud=true`); ML and anomaly are skipped for tier selection. |
| `ML_STRONG_SUSPECT` | `strong_suspect` | XGBoost fraud probability ≥ `threshold_high`. Only for `bank_transfer`. Treated as fraud (`is_fraud=true`). |
| `ML_REVIEW` | `review` | XGBoost probability is between `threshold_low` and `threshold_high`. Needs analyst or user confirmation (`requires_user_confirmation=true`); not auto-declined. |
| `RULE_REVIEW` | `review` | Composite `rule_score` ≥ 50 from soft rules (e.g. `HIGH_AMOUNT` + `NEW_MERCHANT_HIGH` = 70). Queued for review, not auto-declined. |
| `HIGH_ANOMALY` | `review` | Anomaly score ≥ 70 — statistically unusual amount/timing/category for this user. Queued for review. |
| `OUT_OF_SCOPE` | `out_of_scope` | Payment method is `card` or `wallet`; XGBoost was not run. Rules and anomaly still apply, but ML tiers are skipped. Clean approval path if no other condition matched. |

#### Examples

| `flag_reasons` | `risk_tier` | Interpretation |
| -------------- | ----------- | -------------- |
| `["GEO_MISMATCH", "HARD_DECLINE"]` | `block` | IP country mismatch — auto-declined |
| `["HIGH_AMOUNT", "NEW_MERCHANT_HIGH", "RULE_REVIEW"]` | `review` | Two soft rules summed to 70 — manual review |
| `["ML_STRONG_SUSPECT"]` | `strong_suspect` | Model confident fraud on a bank transfer |
| `["HIGH_AMOUNT", "OUT_OF_SCOPE"]` | `out_of_scope` | Card payment with elevated amount, but ML not in scope; approved |
| `[]` | `approve` | No rules triggered, ML low/absent, anomaly below threshold |

## Delivery Semantics

At-least-once Kafka delivery with idempotent `INSERT ... ON CONFLICT` upserts on `transaction_id`.

## Kafka Client

Uses **confluent-kafka** (production-aligned). Single-broker Compose with Zookeeper for cross-platform simplicity; KRaft migration noted as future ops improvement.

## Project Structure

```
producer/          # Generator, FastAPI ingestion, PaySim replay
consumer/          # Stream scoring: validate → FX → rules + XGBoost + anomaly → persist
airflow/dags/      # daily_rescore + fx_rate_refresh
dashboard/         # Streamlit KPIs and stream vs batch comparison
infra/postgres/    # Schema + migrations (tier scoring, FX snapshots)
analysis/          # PaySim training helpers, EDA notebook, data profiling
models/            # fraud_classifier_v1.joblib, anomaly_v1.joblib, training notebook
scripts/           # Train models, seed users, wait-for
shared/            # Event schema, FX conversion, PaySim transforms
tests/             # Unit tests
docs/              # Requirements, schema, architecture
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
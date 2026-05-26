# Real-Time Fraud Detection

A real-time fraud detection pipeline: synthetic transactions (based on PaySim dataset) flow through **Kafka**, get scored by a stream consumer (**rules + XGBoost + IsolationForest anomaly**), persist to **PostgreSQL**, are re-scored nightly by **Airflow** with a stricter batch ruleset, and feed a **Streamlit** dashboard via **dbt** analytics marts.

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



## Lambda Story


| Layer     | Component          | Version tag              | Purpose                                              |
| --------- | ------------------ | ------------------------ | ---------------------------------------------------- |
| Speed     | Kafka consumer     | `stream_v1`              | Low-latency multi-tier scoring                       |
| ML        | XGBoost classifier | `ml_v1_static` (bundled) | PaySim-trained fraud probability for `bank_transfer` |
| Anomaly   | IsolationForest    | `anomaly_v1`             | Unsupervised outlier score                           |
| Batch     | Airflow DAG        | `batch_v2`               | Stricter re-score into history table                 |
| FX        | Airflow DAG        | —                        | Live FX snapshots every 5 minutes                    |
| Analytics | dbt (`dbt_fraud`)  | `fraud_analytics`        | Staging → marts in Postgres `analytics` schema (Airflow-scheduled) |


## Prerequisites

- Docker Desktop (8 GB+ RAM recommended)
- Python 3.11+ (use **3.12** for both venvs when possible)

### Two virtual environments (recommended)


| Venv             | File                        | Python    | Purpose                                                                        |
| ---------------- | --------------------------- | --------- | ------------------------------------------------------------------------------ |
| `.venv`          | `requirements.txt`          | **3.11+** | Pipeline, API, consumer, dashboard, tests (`-e .[...]` editable install)        |
| `.venv-analysis` | `requirements-analysis.txt` | 3.11+     | PaySim model training, EDA notebooks (includes **XGBoost**; no `-e .` install) |

Install **dbt** into `.venv` when you need analytics marts or the dashboard refresh button:

```powershell
pip install -r requirements-dbt.txt
copy dbt_fraud\profiles.example.yml dbt_fraud\profiles.yml
```


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

# 2. Start infrastructure (builds custom Airflow image with dbt on first run)
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1
# Enable dbt_marts_refresh in Airflow UI — marts rebuild every DBT_REFRESH_INTERVAL_MINUTES (default 10)

# 3. Models (pre-trained classifier bundled; train anomaly if missing)
python scripts/train_anomaly.py
# Optional: retrain classifier from PaySim CSV (uses .venv-analysis + xgboost)
# python scripts/train_fraud_classifier.py

# 4. Start consumer (terminal 1)
python -m consumer.main

# 5. Start generator (terminal 2) — simulation mode by default (see below)
python -m producer.generator

# 6. Build analytics marts + dashboard (after consumer has persisted rows)
pip install -r requirements-dbt.txt
copy dbt_fraud\profiles.example.yml dbt_fraud\profiles.yml
cd dbt_fraud; dbt run --profiles-dir .; cd ..
$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501
```

By default the generator runs in **historical simulation** mode (`GENERATOR_LIVE=false`): it publishes `GENERATOR_SIM_TOTAL` transactions (default **30,000**) with timestamps spread across `GENERATOR_SIM_START` → `GENERATOR_SIM_END`, then exits. Set `GENERATOR_LIVE=true` in `.env` for a continuous live stream at `GENERATOR_RATE_MIN`–`GENERATOR_RATE_MAX` tx/s.

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
python -m producer.paysim_replay                       # full replay
```

## Analytics layer (dbt)

The `dbt_fraud` project transforms OLTP tables (`transactions`, `risk_scores`, `fraud_flags`, `risk_scores_history`) into materialized marts under the Postgres **`analytics`** schema (plus `staging` / `intermediate` views). The Streamlit dashboard reads only from these marts — not raw OLTP tables.

| Layer        | Schema        | Examples                                                                 |
| ------------ | ------------- | ------------------------------------------------------------------------ |
| Staging      | `staging`     | `stg_transactions`, `stg_fraud_flags`, `stg_risk_scores`               |
| Intermediate | `intermediate`| `int_scored_events`, `int_velocity_fraud_events`, `int_flag_reasons`   |
| Marts        | `analytics`   | `mart_general_kpis`, `mart_flag_reasons`, `mart_velocity_kpis`, trends |

**Setup** (once per machine, with Postgres running and `DATABASE_URL` pointing at host port **5433**):

```powershell
pip install -r requirements-dbt.txt
copy dbt_fraud\profiles.example.yml dbt_fraud\profiles.yml
cd dbt_fraud; dbt run --profiles-dir .; cd ..
```

Re-run `dbt run` after new transactions are scored, or let Airflow keep marts fresh automatically. The dashboard **polls Postgres every `DASHBOARD_AUTO_REFRESH_SECONDS`** (default 60s) and reloads charts when KPI marts change — no manual click needed after an Airflow run.

### Scheduled refresh (Airflow)

The **`dbt_marts_refresh`** DAG runs `dbt run` inside the Airflow containers (dbt is baked into the custom Airflow image). Enable it in the Airflow UI at [http://localhost:8081](http://localhost:8081).

Configure the schedule in `.env`:


| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `DBT_REFRESH_ENABLED` | `true` | Set `false` to disable the schedule (manual triggers only) |
| `DBT_REFRESH_INTERVAL_MINUTES` | `10` | Cron every *N* minutes (`*/N * * * *`, N = 1–59) |
| `DBT_REFRESH_SCHEDULE` | *(empty)* | Optional full cron expression; overrides interval when set |
| `DASHBOARD_AUTO_REFRESH_SECONDS` | `60` | How often the Streamlit UI polls Postgres for updated KPI marts |

Examples:

```env
DBT_REFRESH_INTERVAL_MINUTES=10    # every 10 minutes (default)
DBT_REFRESH_INTERVAL_MINUTES=5     # every 5 minutes
DBT_REFRESH_SCHEDULE=*/15 * * * *  # every 15 minutes (explicit cron)
DBT_REFRESH_ENABLED=false          # manual refresh only
```

After changing schedule variables, recreate Airflow containers so the scheduler picks up the new cron:

```powershell
docker compose up -d --build airflow-scheduler airflow-webserver
```

Airflow connects to Postgres at `postgres:5432` via `dbt_fraud/profiles/airflow/profiles.yml`. Local CLI and the dashboard **Run dbt locally** button use `dbt_fraud/profiles.yml` on `localhost:5433`. Charts reload automatically when Airflow finishes a rebuild.

Optional local dbt commands:

```powershell
cd dbt_fraud
dbt test --profiles-dir .
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
cd ..
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

Watch Kafka UI at [http://localhost:8080](http://localhost:8080) — messages on `transactions.raw` and `transactions.scored`. In simulation mode the generator stops after its target count; use `GENERATOR_LIVE=true` if you want a never-ending stream.

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
"SELECT ff.transaction_id, risk_tier, is_fraud, flag_reasons, ff.ml_prob, final_score 
FROM fraud_flags ff 
JOIN risk_scores rs ON rs.transaction_id = ff.transaction_id 
WHERE ff.transaction_id = '11111111-1111-1111-1111-111111111111'
ORDER BY ff.scored_at DESC 
LIMIT 5;"
```

### Cleanup — delete a test transaction from Postgres

After verifying the fraud flag, remove the demo payload so it does not skew dashboards or batch comparisons. The FastAPI ingestion API exposes a cascade delete that removes the transaction and **all related rows** in one atomic DB transaction:


| Table removed from    | Notes                           |
| --------------------- | ------------------------------- |
| `risk_scores_history` | All batch re-scores for this ID |
| `fraud_flags`         | Flag + `flag_reasons`           |
| `risk_scores`         | Stream scores                   |
| `transactions`        | Core transaction row            |


**Requirements:** the API must be running (`uvicorn producer.api.main:app --host 0.0.0.0 --port 8000 --reload`), and the consumer must have already processed the event so rows exist in Postgres.

```powershell
# Delete the Step 3 demo transaction (replace with your transaction_id)
curl -X DELETE http://localhost:8000/transactions/11111111-1111-1111-1111-111111111111
```

**200 — deleted:**

```json
{
  "status": "deleted",
  "transaction_id": "11111111-1111-1111-1111-111111111111",
  "deleted_rows": {
    "risk_scores_history": 0,
    "fraud_flags": 1,
    "risk_scores": 1,
    "transactions": 1
  }
}
```

**404** — transaction not found (consumer has not persisted it yet, or ID typo).

This only removes Postgres data. Messages already on Kafka topics (`transactions.raw`, `transactions.scored`) are unchanged; for a full local reset, run `docker compose down -v` and bring the stack back up.

### Step 5 — Dashboard + Airflow batch re-score

1. Build analytics marts and open the dashboard:

```powershell
cd dbt_fraud; dbt run --profiles-dir .; cd ..
$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501
```

Open [http://localhost:8501](http://localhost:8501) — **General Overview** (KPIs, merchants, countries, rule breakdown, trends) and **Velocity Deep-Dive** (velocity KPIs, buckets, repeat intervals, heatmaps). Marts rebuild via Airflow **`dbt_marts_refresh`** (default every 10 minutes); the dashboard reloads within **`DASHBOARD_AUTO_REFRESH_SECONDS`** (default 60s) after KPI data changes. Use **Reload charts** for an immediate refresh.

2. Open [http://localhost:8081](http://localhost:8081) (admin/admin). Enable **`dbt_marts_refresh`**, **`fx_rate_refresh`** (needs `FX_API_KEY`), and **`daily_rescore`**.

3. Compare stream vs batch in SQL:

```sql
SELECT rs.final_score AS stream_score, rsh.final_score AS batch_score
FROM risk_scores rs
JOIN risk_scores_history rsh ON rsh.transaction_id = rs.transaction_id
LIMIT 10;
```

## Common commands (PowerShell)

Run from the repo root with `.venv` activated unless noted.

| Task | Command |
| ---- | ------- |
| Start infrastructure | `docker compose up -d` then `powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1` |
| Tear down (with volumes) | `docker compose down -v` |
| Wait for services | `powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1` |
| Stream consumer | `python -m consumer.main` |
| Synthetic generator | `python -m producer.generator` |
| PaySim replay | `python -m producer.paysim_replay` |
| FastAPI ingestion | `uvicorn producer.api.main:app --host 0.0.0.0 --port 8000 --reload` |
| Streamlit dashboard | `$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501` |
| Reload dashboard charts | Click **Reload charts** in the sidebar (reads Postgres only) |
| Build dbt marts (local) | `cd dbt_fraud; dbt run --profiles-dir .; cd ..` |
| dbt marts (Airflow) | Enable **`dbt_marts_refresh`** DAG; schedule via `DBT_REFRESH_INTERVAL_MINUTES` in `.env` |
| dbt tests | `cd dbt_fraud; dbt test --profiles-dir .; cd ..` |
| dbt docs | `cd dbt_fraud; dbt docs generate --profiles-dir .; dbt docs serve --profiles-dir .; cd ..` |
| Unit tests | `pytest tests/ -v` |
| Train IsolationForest | `python scripts/train_anomaly.py` |
| Seed user history | `python scripts/seed_users.py` |
| Data profile | `python analysis/profile_data.py` |
| Docker logs (follow) | `docker compose logs -f` |


Train the supervised classifier separately:

```powershell
python scripts/train_fraud_classifier.py   # writes models/fraud_classifier_v1.joblib
```

## Scoring Pipeline

After FX conversion, each valid event passes through three scorers — **rules**, **XGBoost**, and **anomaly** — then a **multi-signal tier cascade** picks the outcome. All signals are evaluated; the highest applicable tier wins (not first-match-wins).

```
hard-decline rules?              →  block
ML prob ≥ t_high?                →  strong_suspect   (bank_transfer only)
rule_score ≥ 85?                 →  strong_suspect
2+ soft signals (ML/rules/anomaly)? →  review
1 soft signal?                   →  approve (logged as SOFT_SIGNAL_OBSERVED)
not bank_transfer, no signals?   →  out_of_scope
else                             →  approve
```

**Soft signals** (each counts independently toward review):

| Signal | Bank transfer | Card / wallet (stricter) |
| ------ | ------------- | ------------------------ |
| ML prob in `[t_low, t_high)` | Yes | N/A (ML out of scope) |
| Rule score in `[soft, 85)` | ≥ 50 | ≥ 60 |
| Anomaly score | ≥ 70 | ≥ 80 |


| Tier | Name             | `is_fraud` | `is_flagged` | User confirmation                                |
| ---- | ---------------- | ---------- | ------------ | ------------------------------------------------ |
| 0    | `out_of_scope`   | No         | No           | No — card/wallet with no soft signals            |
| 1    | `block`          | Yes        | Yes          | No — hard-decline rules                          |
| 2    | `strong_suspect` | Yes        | Yes          | No — ML prob ≥ `t_high` or rule score ≥ 85       |
| 3    | `review`         | No         | Yes          | Yes — 2+ soft signals (`MULTI_SIGNAL_REVIEW`)  |
| 4    | `approve`        | No         | No*          | No — clean or single soft signal (audit logged)  |

\*Single soft signals are approved but include `SOFT_SIGNAL_OBSERVED` in `flag_reasons` for audit.


Persisted `flag_reasons` (JSON array on `fraud_flags`) explain **why** the tier was chosen. A transaction can carry multiple reasons — e.g. `["GEO_MISMATCH", "HARD_DECLINE"]` when geo mismatch triggers an immediate block.

### Rulesets: `stream_v1` vs `batch_v2`

Both rulesets evaluate the same four rules with identical weights. They differ in **thresholds** and **where they run**:


|                         | Stream (`stream_v1`)             | Batch (`batch_v2`)                 |
| ----------------------- | -------------------------------- | ---------------------------------- |
| **Runs in**             | Kafka consumer (real-time)       | Airflow `daily_rescore` DAG        |
| **Velocity limit**      | > 5 tx/user/hour                 | > 3 tx/user/hour                   |
| **Amount P99 fallback** | Global $850 (or user 30-day P99) | Global × 0.85 (or user P99 × 0.85) |
| **Amount P95 fallback** | Global $450 (or user 30-day P95) | Global × 0.85 (or user P95 × 0.85) |
| **Output table**        | `risk_scores` + `fraud_flags`    | `risk_scores_history`              |


**How `rule_score` is computed:** each triggered rule adds its weight; the sum is capped at 100. Multiple rules can fire on one transaction (e.g. high amount + geo mismatch → score 90).

**User context loaded from Postgres** (per event):

- `tx_count_1h` — transactions for this user in the rolling hour before the event timestamp
- `amount_p99` / `amount_p95` — user percentiles over the last 30 days (USD); falls back to global defaults when no history
- `seen_merchants` — distinct merchants this user has transacted with before

Override defaults via `.env`: `VELOCITY_1H_LIMIT`, `GLOBAL_AMOUNT_P95`, `GLOBAL_AMOUNT_P99`, `RULE_SOFT_THRESHOLD` (50), `RULE_STRONG_SUSPECT_THRESHOLD` (85), `ANOMALY_SOFT_THRESHOLD` (70), `SOFT_SIGNALS_REQUIRED` (2), `CARD_WALLET_RULE_SOFT_THRESHOLD` (60), `CARD_WALLET_ANOMALY_SOFT_THRESHOLD` (80).

### Rules reference


| Rule                | Weight | Hard decline | What it detects                                                                                                                                                                                                                                          |
| ------------------- | ------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HIGH_AMOUNT`       | 40     | No           | Transaction exceeds the user's normal spending. Fires when `amount_usd` is above the user's 30-day 99th percentile; new users use the global P99 ($850 stream / ~$723 batch). Catches sudden large purchases or account takeover spend-down.             |
| `VELOCITY_1H`       | 35     | **Yes**      | Too many transactions in a short window — classic card-testing or burst fraud. Fires when the user has more than 5 tx in the prior hour (stream) or 3 (batch). Counts existing Postgres rows, so synthetic velocity fraud needs prior txs in the window. |
| `GEO_MISMATCH`      | 50     | **Yes**      | Billing country differs from IP geolocation. Fires when `country ≠ ip_country` (e.g. card registered in US, IP in RU). Strong signal for stolen credentials or VPN/proxy abuse.                                                                          |
| `NEW_MERCHANT_HIGH` | 30     | No           | First purchase at an unseen merchant for a large amount. Fires when `merchant_id` is new to the user **and** `amount_usd` exceeds the user's P95 (or global $450 / ~$383 batch). Catches mule payouts or first-time high-value merchant fraud.           |


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

An anomaly score ≥ soft threshold counts as one **soft signal** toward multi-signal review (70 for bank transfer, 80 for card/wallet). A single anomaly signal alone approves with `SOFT_SIGNAL_OBSERVED`.

### Final score

`final_score = max(rule_score, anomaly_score, ml_prob × 100)` — used for dashboards and batch comparison; **tier assignment** (not `final_score` alone) drives `is_fraud`, `is_flagged`, and `requires_user_confirmation`.

### Flag reasons reference

`flag_reasons` is the audit trail stored on each scored transaction. Values fall into two groups: **rule hits** (which rules fired) and **tier drivers** (why that tier was chosen).

#### Rule hits

These appear whenever the corresponding rule triggers. They can coexist with tier-driver reasons.


| Reason              | Source       | Meaning                                                                                                                                                                                                                  |
| ------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `HIGH_AMOUNT`       | Rules engine | `amount_usd` exceeded the user's P99 (or global fallback). Contributes +40 to `rule_score`. Alone it usually lands in `approve` unless combined with other signals; at +40 it stays below the 50-point review threshold. |
| `VELOCITY_1H`       | Rules engine | User exceeded the hourly transaction count. Contributes +35 and triggers **hard decline** → tier `block` with `HARD_DECLINE` also appended.                                                                              |
| `GEO_MISMATCH`      | Rules engine | `country` and `ip_country` differ. Contributes +50 and triggers **hard decline** → tier `block`.                                                                                                                         |
| `NEW_MERCHANT_HIGH` | Rules engine | First-time merchant for this user with amount above P95. Contributes +30. Soft rule — does not hard-decline on its own.                                                                                                  |


#### Tier drivers

These are appended by the tier cascade to explain the **decision**, not just which rules fired.


| Reason                  | Tier             | Meaning                                                                                                                                                         |
| ----------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HARD_DECLINE`          | `block`          | A hard-decline rule (`GEO_MISMATCH` or `VELOCITY_1H`) fired. `is_fraud=true`, `is_flagged=true`.                                                                |
| `ML_STRONG_SUSPECT`     | `strong_suspect` | XGBoost fraud probability ≥ `threshold_high` (bank_transfer only). `is_fraud=true`.                                                                             |
| `RULE_STRONG_SUSPECT`   | `strong_suspect` | Composite `rule_score` ≥ 85. `is_fraud=true`.                                                                                                                   |
| `ML_SOFT`               | soft signal      | ML probability in `[t_low, t_high)`. Contributes one soft signal.                                                                                               |
| `RULE_SOFT`             | soft signal      | Rule score in `[soft_threshold, 85)`. Contributes one soft signal.                                                                                              |
| `ANOMALY_SOFT`          | soft signal      | Anomaly score ≥ soft threshold. Contributes one soft signal.                                                                                                     |
| `MULTI_SIGNAL_REVIEW`   | `review`         | Two or more soft signals fired. `is_flagged=true`, `requires_user_confirmation=true`.                                                                           |
| `SOFT_SIGNAL_OBSERVED`  | `approve`        | Exactly one soft signal — approved but logged for audit.                                                                                                        |
| `OUT_OF_SCOPE`          | `out_of_scope`   | Card/wallet with no soft signals; ML not evaluated.                                                                                                             |


#### Examples


| `flag_reasons`                                                              | `risk_tier`      | Interpretation                                              |
| ----------------------------------------------------------------------------- | ---------------- | ----------------------------------------------------------- |
| `["GEO_MISMATCH", "HARD_DECLINE"]`                                            | `block`          | IP country mismatch — auto-declined                         |
| `["HIGH_AMOUNT", "RULE_SOFT", "ANOMALY_SOFT", "MULTI_SIGNAL_REVIEW"]`         | `review`         | Rule + anomaly soft signals — manual review                 |
| `["ML_STRONG_SUSPECT"]`                                                       | `strong_suspect` | Model confident fraud on a bank transfer                    |
| `["HIGH_AMOUNT", "ML_SOFT", "SOFT_SIGNAL_OBSERVED"]`                            | `approve`        | Single ML soft signal — approved with audit trail           |
| `["HIGH_AMOUNT", "OUT_OF_SCOPE"]`                                             | `out_of_scope`   | Card payment, amount elevated but no soft signals           |
| `[]`                                                                          | `approve`        | No rules triggered, ML low/absent, anomaly below threshold  |


## Delivery Semantics

At-least-once Kafka delivery with idempotent `INSERT ... ON CONFLICT` upserts on `transaction_id`.

## Kafka Client

Uses **confluent-kafka** (production-aligned). Single-broker Compose with Zookeeper for cross-platform simplicity; KRaft migration noted as future ops improvement.

## Project Structure

```
producer/          # Generator, FastAPI ingestion, PaySim replay
consumer/          # Stream scoring: validate → FX → rules + XGBoost + anomaly → persist
airflow/dags/      # daily_rescore, fx_rate_refresh, dbt_marts_refresh
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
- **Warehouse:** Export Postgres analytics to Snowflake (dbt marts are Postgres-native today)
- **Stream processing:** Secondary consumer in Spark Structured Streaming
- **Ops:** KRaft mode, exactly-once semantics, auth, multi-region
- **Dashboard:** Stream vs batch comparison mart wired into the UI

## License

MIT
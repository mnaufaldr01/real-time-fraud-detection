# Setup and operations

## Prerequisites

- Docker Desktop (8 GB+ RAM recommended)
- Python **3.11+** (3.12 recommended)

## Virtual environments

| Venv | File | Purpose |
| ---- | ---- | ------- |
| `.venv` | `requirements.txt` | Pipeline: consumer, producer, API, dashboard, tests |
| `.venv-analysis` | `requirements-analysis.txt` | PaySim training, EDA notebooks (XGBoost tuning) |
| *(optional in `.venv`)* | `requirements-dbt.txt` | dbt CLI for local mart builds |

### Pipeline venv

```powershell
copy .env.example .env
# Docker Postgres is on host port 5433:
# DATABASE_URL=postgresql://fraud:fraud@localhost:5433/fraud_db

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` installs the project editable with `[api,consumer,producer,analysis,dashboard,dev]` and pins runtime deps including **xgboost**, **confluent-kafka**, **scikit-learn**, **streamlit**, etc. See [dependencies.md](dependencies.md).

### Analysis venv

```powershell
py -3.12 -m venv .venv-analysis
.\.venv-analysis\Scripts\Activate.ps1
pip install -r requirements-analysis.txt
python -m ipykernel install --user --name=fraud-analysis --display-name "Fraud Detection (analysis)"
```

### dbt (local marts)

```powershell
pip install -r requirements-dbt.txt
copy dbt_fraud\profiles.example.yml dbt_fraud\profiles.yml
```

## Quick start

```powershell
# 1. Env + Python deps (see above)

# 2. Infrastructure
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1
# Enable dbt_marts_refresh in Airflow UI

# 3. Models
python scripts/train_anomaly.py

# 4. Consumer (terminal 1)
python -m consumer.main

# 5. Generator (terminal 2) — simulation by default
python -m producer.generator

# 6. Marts + dashboard (after data flows)
cd dbt_fraud; dbt run --profiles-dir .; cd ..

# React dashboard (recommended)
uvicorn analytics_api.main:app --host 0.0.0.0 --port 8001 --reload
# new terminal:
cd frontend; npm install; npm run dev

# Legacy Streamlit
$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501
```

**Generator modes:** `GENERATOR_LIVE=false` (default) publishes `GENERATOR_SIM_TOTAL` txs across `GENERATOR_SIM_START`–`GENERATOR_SIM_END` then exits. Set `GENERATOR_LIVE=true` for continuous streaming.

Apply Postgres migration for `is_flagged` on existing volumes:

```powershell
Get-Content infra\postgres\init\007_is_flagged.sql | docker compose exec -T postgres psql -U fraud -d fraud_db
```

## Service URLs

| Service | URL | Credentials |
| ------- | --- | ------------- |
| Kafka UI | http://localhost:8080 | — |
| Airflow | http://localhost:8081 | admin / admin |
| FastAPI (ingestion) | http://localhost:8000/docs | — |
| Analytics API | http://localhost:8001/docs | — |
| React dashboard | http://localhost:5173 (dev) / http://localhost:3000 (Docker) | — |
| Streamlit (legacy) | http://localhost:8501 | — |
| PostgreSQL | localhost:**5433** | fraud / fraud |

## Multi-currency

Events carry local `amount` + `currency`. The **consumer** converts to USD using `fx_rate_snapshots` (Airflow `fx_rate_refresh` every 5 min). Set `FX_API_KEY` in `.env`. Publishers use static fallbacks from `shared/fx.py` for synthetic amounts.

```powershell
python -m producer.paysim_replay --limit 1000
python -m producer.paysim_replay --sample-rate 0.01
```

## Airflow troubleshooting

### Task log shows `403 FORBIDDEN` / `secret_key`

Webserver and scheduler must share the same `AIRFLOW__WEBSERVER__SECRET_KEY`. This repo sets it via `docker-compose.yml` (`AIRFLOW_WEBSERVER_SECRET_KEY` in `.env` optional). After changing it, recreate Airflow containers:

```powershell
docker compose up -d --force-recreate airflow-webserver airflow-scheduler
```

Task logs are also written under **`airflow/logs/`** on the host (same mount in webserver and scheduler).

### `check_training_data` failed (real error)

Usually missing PaySim data: place `PS_20174392719_1491204439457_log.csv` in `producer/sample_dataset/`, or run `scripts/train_fraud_classifier.py` once to create `analysis/cache/paysim_transformed_transfer_cashout.parquet`.

### `evaluate_holdout` / XGBoost unpickle error

Production classifier may have been trained with a different XGBoost than the Airflow image. Export a metrics sidecar: `python scripts/export_classifier_metrics.py`, then retry the DAG. See [ml_retrain.md](ml_retrain.md).

### `promote_or_skip` PermissionError on copy

On Docker Desktop (Windows), `shutil.copy2` can fail when updating timestamps on bind-mounted `models/`. The DAG uses `copyfile` as a fallback automatically; retry `promote_or_skip` after pulling the latest code.

## Common commands

| Task | Command |
| ---- | ------- |
| Start stack | `docker compose up -d` + `scripts/wait-for.ps1` |
| Tear down | `docker compose down -v` |
| Consumer | `python -m consumer.main` |
| Generator | `python -m producer.generator` |
| PaySim replay | `python -m producer.paysim_replay` |
| API (ingestion) | `uvicorn producer.api.main:app --host 0.0.0.0 --port 8000 --reload` |
| Analytics API | `uvicorn analytics_api.main:app --host 0.0.0.0 --port 8001 --reload` |
| React dashboard | `cd frontend; npm run dev` |
| Streamlit (legacy) | `$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501` |
| dbt marts | `cd dbt_fraud; dbt run --profiles-dir .; cd ..` |
| Unit tests | `pytest tests/unit -v` |
| Lint | `ruff check .` |
| Train anomaly | `python scripts/train_anomaly.py` |
| Train classifier | `python scripts/train_fraud_classifier.py` (`.venv-analysis` recommended) |

## Testing

```powershell
pytest tests/unit -v
ruff check .
```

CI: `.github/workflows/ci.yml`

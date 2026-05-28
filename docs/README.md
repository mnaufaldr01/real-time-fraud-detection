# Documentation index

Start here after the [README](../README.md) quick start. All paths are relative to this `docs/` folder unless noted.

## Getting started

| Doc | When to read |
| --- | ------------ |
| [setup.md](setup.md) | Install, Docker Compose, **service URLs**, env vars, common commands |
| [demo.md](demo.md) | End-to-end demo: ingest → consumer → dashboard |
| [architecture.md](architecture.md) | Lambda layout (stream vs batch vs analytics) |

## Airflow (batch & MLOps)

**UI:** http://localhost:8081 — login `admin` / `admin` (see [setup.md](setup.md#service-urls)).

| Doc | When to read |
| --- | ------------ |
| [setup.md § Airflow troubleshooting](setup.md#airflow-troubleshooting) | Task log 403, `promote_or_skip` permissions, missing PaySim data |
| [demo.md § Step 5](demo.md) | Which DAGs to enable in the UI |
| [ml_retrain.md](ml_retrain.md) | **`model_retrain_weekly`** — safe deployment retrain, promote gates, XGBoost alignment |
| [analytics.md § Airflow refresh](analytics.md#airflow-refresh) | **`dbt_marts_refresh`** schedule and env vars |

| DAG (`airflow/dags/`) | Schedule | Doc |
| --------------------- | -------- | --- |
| `fx_rate_refresh` | Every 5 min | [setup.md](setup.md#multi-currency) — needs `FX_API_KEY` |
| `dbt_marts_refresh` | Configurable (`DBT_REFRESH_*`) | [analytics.md](analytics.md#airflow-refresh) |
| `daily_rescore` | Daily | [scoring.md § Rulesets](scoring.md#rulesets-stream_v1-vs-batch_v2), [architecture.md](architecture.md) |
| `model_retrain_weekly` | Weekly (optional) | [ml_retrain.md](ml_retrain.md) |

After changing `airflow/requirements.txt`, rebuild: `docker compose build airflow-scheduler airflow-webserver`.

## Stream scoring & ML

| Doc | When to read |
| --- | ------------ |
| [scoring.md](scoring.md) | Tiers, rules, XGBoost, anomaly, `flag_reasons`, env thresholds |
| [ml_retrain.md](ml_retrain.md) | Offline / Airflow model bundles under `models/` |
| [data_profile.md](data_profile.md) | PaySim profiling notes |

## Analytics & dashboard

| Doc | When to read |
| --- | ------------ |
| [analytics.md](analytics.md) | dbt layers, marts, KPI definitions, local `dbt run` |
| [demo.md](demo.md) | Streamlit dashboard |

## Reference

| Doc | When to read |
| --- | ------------ |
| [dependencies.md](dependencies.md) | `requirements.txt` vs Airflow image vs `requirements-dbt.txt` |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Functional requirements checklist |
| [event_schema.json](event_schema.json) | Kafka transaction JSON schema |

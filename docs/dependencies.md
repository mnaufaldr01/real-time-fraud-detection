# Python dependencies

## Files

| File | Install into | Scope |
| ---- | ------------ | ----- |
| `requirements.txt` | `.venv` | Full pipeline + dashboard + tests |
| `requirements-analysis.txt` | `.venv-analysis` | Training notebooks, `paysim_training.py`, EDA |
| `requirements-dbt.txt` | `.venv` (optional) | dbt CLI only |
| `pyproject.toml` | via `pip install -e .[extras]` | Package metadata and optional dependency groups |

## What `requirements.txt` covers

Pinned installs include everything needed to run:

| Component | Key packages |
| --------- | ------------ |
| **Consumer** | `confluent-kafka`, `pydantic`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `numpy`, `pandas`, `scikit-learn`, `joblib`, **`xgboost`** |
| **Producer / API** | `faker`, `fastapi`, `uvicorn`, `confluent-kafka` |
| **Dashboard** | `streamlit`, `pandas`, `plotly`, `sqlalchemy`, `psycopg2-binary` |
| **Analysis helpers** | `matplotlib`, `seaborn` (for `analysis/profile_data.py`) |
| **Dev** | `pytest`, `ruff`, `httpx` |

Editable install: `-e .[api,consumer,producer,analysis,dashboard,dev]` links `consumer`, `producer`, `shared`, `dashboard`, and **`analysis`** into the venv.

**Not in `requirements.txt`:** Apache Airflow (runs in Docker image), dbt (separate file).

## Runtime import map

| Module | Third-party imports |
| ------ | ------------------- |
| `consumer.main` | `confluent-kafka`, `sqlalchemy` |
| `consumer.classifier` | `pandas`, `joblib`, `xgboost` (load bundle), `analysis.paysim_training` |
| `consumer.anomaly` | `numpy`, `sklearn`, `joblib` |
| `producer.generator` | `faker`, `confluent-kafka` |
| `producer.api` | `fastapi`, `confluent-kafka`, `sqlalchemy` |
| `dashboard` | `streamlit`, `pandas`, `plotly`, `sqlalchemy` |
| `scripts/train_anomaly.py` | `sklearn`, `joblib`, `numpy` |
| `scripts/train_fraud_classifier.py` | `pandas` + `analysis.paysim_training` (needs **xgboost** — use `.venv-analysis` or main venv) |

## Two-venv workflow

- **`.venv`** — run consumer, generator, dashboard, unit tests; XGBoost inference is included.
- **`.venv-analysis`** — retrain classifier, run `model-training.ipynb`; adds `ipykernel`, `kagglehub`, etc.

You do **not** need a separate `pip install xgboost` after `pip install -r requirements.txt`.

## Verify install

```powershell
.\.venv\Scripts\python.exe -c "import confluent_kafka, xgboost, sklearn, streamlit, pandas; print('ok')"
.\.venv\Scripts\python.exe -c "from consumer.scoring import compute_tier_score; print('ok')"
```

## Regenerating pins

After changing `pyproject.toml` extras, refresh the lockfile-style pins:

```powershell
pip install -e ".[api,consumer,producer,analysis,dashboard,dev]"
pip freeze > requirements.txt
# Re-add the editable line and header comments at the top
```

Or use `pip-compile` if you adopt it later.

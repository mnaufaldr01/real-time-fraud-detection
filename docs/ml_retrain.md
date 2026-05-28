# Weekly model retrain (`model_retrain_weekly`)

**Purpose:** safe deployment (gated promote), not production continuous learning. Training data is static PaySim / cache plus synthetic anomaly data — the same sources as `scripts/train_fraud_classifier.py` and `scripts/train_anomaly.py`. The DAG exists to rebuild artifacts, validate candidates offline, and avoid blindly overwriting a good production bundle.

Airflow DAG with five tasks:

```
check_training_data → train_classifier → train_anomaly → evaluate_holdout → promote_or_skip → record_manifest
```

## Prerequisites

- Airflow webserver and scheduler recreated after compose changes (shared `AIRFLOW__WEBSERVER__SECRET_KEY` and `airflow/logs` mount — see [setup.md](setup.md#airflow-troubleshooting)).
- PaySim CSV: `producer/sample_dataset/PS_20174392719_1491204439457_log.csv`, **or**
- Feature cache: `analysis/cache/paysim_transformed_transfer_cashout.parquet` (from a prior `scripts/train_fraud_classifier.py` run)
- Rebuild Airflow image after `airflow/requirements.txt` changes (`pandas`, `pyarrow`, `xgboost`)

## Promotion policy

| Model | Criterion |
| ----- | --------- |
| Classifier | Promote if no production bundle, or candidate **test PR-AUC** ≥ production + `MODEL_RETRAIN_MIN_PR_AUC_DELTA` (metrics read from `*.metrics.json` sidecars when present) |
| Anomaly | Promote when staging train succeeds (synthetic data; no holdout metric) |

Staging artifacts: `models/staging/fraud_classifier_candidate.joblib`, `models/staging/anomaly_candidate.joblib`  
Production: `models/fraud_classifier_v1.joblib`, `models/anomaly_v1.joblib`

Summary written to `models/retrain_manifest.json`. Restart the **fraud consumer** after promotion so joblib bundles reload.

### Fix `production_metrics_unavailable`

Airflow compares **test PR-AUC** via `fraud_classifier_v1.metrics.json`, not by loading the production joblib (avoids XGBoost pickle errors across versions).

**Option A — export sidecar (keep existing production joblib)**

On a machine with the project venv and the same XGBoost used to train the bundle:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/export_classifier_metrics.py --model models/fraud_classifier_v1.joblib
```

Creates `models/fraud_classifier_v1.metrics.json`. Re-run the DAG from **`evaluate_holdout`** (or clear and re-run the full DAG).

**Option B — align XGBoost in Airflow (recommended long-term)**

Rebuild Airflow after `airflow/requirements.txt` changes (pinned to `xgboost==3.2.0` like the app venv):

```powershell
docker compose build --no-cache airflow-scheduler airflow-webserver
docker compose up -d airflow-scheduler airflow-webserver
```

Then run the full `model_retrain_weekly` DAG so staging and production bundles share the same library version. New training runs always write a `.metrics.json` sidecar next to the candidate.

**Option C — promote Airflow-trained classifier only**

If you are fine replacing local production with the last staging candidate, manually copy:

`models/staging/fraud_classifier_candidate.joblib` → `models/fraud_classifier_v1.joblib`  
(and the matching `fraud_classifier_candidate.metrics.json` → `fraud_classifier_v1.metrics.json`)

Restart the fraud consumer afterward.

If production metrics are still unavailable, **classifier promotion is skipped** (anomaly may still promote).

## Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `MODEL_RETRAIN_SCHEDULE` | `0 4 * * 0` | Cron (Sunday 04:00 UTC) |
| `MODEL_RETRAIN_SAMPLE_ROWS` | `0` (all rows) | Cap PaySim rows for faster demo runs; set `100000` in `.env.example` |
| `MODEL_RETRAIN_MAX_TRAIN_ROWS` | `500000` | Chronological train cap inside `train_and_export` |
| `MODEL_RETRAIN_MIN_PR_AUC_DELTA` | `0.0` | Minimum PR-AUC improvement to replace classifier |
| `MODEL_RETRAIN_TUNE` | off | Enable RandomizedSearchCV (slow) |
| `MODEL_RETRAIN_ROOT` | repo root / `/opt/airflow` in Docker | Project root for paths |

Implementation: [`shared/model_retrain.py`](../shared/model_retrain.py), DAG [`airflow/dags/model_retrain_weekly.py`](../airflow/dags/model_retrain_weekly.py).

## Future enhancement

Not planned in the current pipeline: extract labeled rows from Postgres (confirmed fraud + vetted negatives), undersample the majority class to match fraud count, optional hyperparameter tuning on that dataset, time-based holdout, and promote when metrics beat production. See the README **Model retrain** section for rationale (avoid retraining on stream `is_fraud` labels alone).

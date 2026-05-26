# Weekly model retrain (`model_retrain_weekly`)

**Purpose:** safe deployment (gated promote), not production continuous learning. Training data is static PaySim / cache plus synthetic anomaly data — the same sources as `scripts/train_fraud_classifier.py` and `scripts/train_anomaly.py`. The DAG exists to rebuild artifacts, validate candidates offline, and avoid blindly overwriting a good production bundle.

Airflow DAG with five tasks:

```
check_training_data → train_classifier → train_anomaly → evaluate_holdout → promote_or_skip → record_manifest
```

## Prerequisites

- PaySim CSV: `producer/sample_dataset/PS_20174392719_1491204439457_log.csv`, **or**
- Feature cache: `analysis/cache/paysim_transformed_transfer_cashout.parquet` (from a prior `scripts/train_fraud_classifier.py` run)
- Rebuild Airflow image after `airflow/requirements.txt` changes (`pandas`, `pyarrow`, `xgboost`)

## Promotion policy

| Model | Criterion |
| ----- | --------- |
| Classifier | Promote if no production bundle, or candidate **test PR-AUC** ≥ production + `MODEL_RETRAIN_MIN_PR_AUC_DELTA` |
| Anomaly | Promote when staging train succeeds (synthetic data; no holdout metric) |

Staging artifacts: `models/staging/fraud_classifier_candidate.joblib`, `models/staging/anomaly_candidate.joblib`  
Production: `models/fraud_classifier_v1.joblib`, `models/anomaly_v1.joblib`

Summary written to `models/retrain_manifest.json`. Restart the **fraud consumer** after promotion so joblib bundles reload.

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

"""Safe-deployment model retrain helpers (Airflow DAG + offline scripts).

Trains on static PaySim/cache and synthetic anomaly data — not live Postgres labels.
Promotion gates replace production joblib only when offline metrics improve.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.model_metrics import classifier_metrics_sidecar_path, read_test_pr_auc

logger = logging.getLogger(__name__)

PAYSIM_CSV_NAME = "PS_20174392719_1491204439457_log.csv"


def project_root() -> Path:
    override = os.getenv("MODEL_RETRAIN_ROOT", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent


def paysim_csv_path() -> Path:
    override = os.getenv("PAYSIM_CSV_PATH", "").strip()
    if override:
        return Path(override)
    return project_root() / "producer" / "sample_dataset" / PAYSIM_CSV_NAME


def feature_cache_path() -> Path:
    override = os.getenv("MODEL_RETRAIN_CACHE_PATH", "").strip()
    if override:
        return Path(override)
    return (
        project_root()
        / "analysis"
        / "cache"
        / "paysim_transformed_transfer_cashout.parquet"
    )


def classifier_staging_path() -> Path:
    return Path(
        os.getenv(
            "MODEL_RETRAIN_CLASSIFIER_STAGING",
            str(project_root() / "models" / "staging" / "fraud_classifier_candidate.joblib"),
        )
    )


def classifier_production_path() -> Path:
    return Path(
        os.getenv(
            "CLASSIFIER_MODEL_PATH",
            str(project_root() / "models" / "fraud_classifier_v1.joblib"),
        )
    )


def anomaly_staging_path() -> Path:
    return Path(
        os.getenv(
            "MODEL_RETRAIN_ANOMALY_STAGING",
            str(project_root() / "models" / "staging" / "anomaly_candidate.joblib"),
        )
    )


def anomaly_production_path() -> Path:
    return Path(
        os.getenv(
            "ANOMALY_MODEL_PATH",
            str(project_root() / "models" / "anomaly_v1.joblib"),
        )
    )


def retrain_manifest_path() -> Path:
    return Path(
        os.getenv(
            "MODEL_RETRAIN_MANIFEST",
            str(project_root() / "models" / "retrain_manifest.json"),
        )
    )


def _ensure_project_on_path() -> None:
    root = str(project_root())
    import sys

    if root not in sys.path:
        sys.path.insert(0, root)


def check_training_data() -> dict[str, Any]:
    """Verify PaySim CSV or feature cache exists for classifier training."""
    csv_path = paysim_csv_path()
    cache_path = feature_cache_path()
    csv_ok = csv_path.is_file()
    cache_ok = cache_path.is_file()

    if not csv_ok and not cache_ok:
        raise FileNotFoundError(
            "PaySim training data missing. Place "
            f"{PAYSIM_CSV_NAME} under producer/sample_dataset/ "
            f"(expected {csv_path}) or provide a feature cache at {cache_path}."
        )

    return {
        "csv_path": str(csv_path),
        "csv_present": csv_ok,
        "cache_path": str(cache_path),
        "cache_present": cache_ok,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def run_classifier_training() -> dict[str, Any]:
    """Train XGBoost classifier to staging path (uses analysis.paysim_training)."""
    _ensure_project_on_path()
    import pandas as pd

    from analysis.paysim_training import (
        file_sha256,
        train_and_export,
        transform_paysim_dataframe,
    )

    csv_path = paysim_csv_path()
    cache_path = feature_cache_path()
    staging = classifier_staging_path()
    sample_rows = int(os.getenv("MODEL_RETRAIN_SAMPLE_ROWS", "0") or "0")
    use_cache = os.getenv("MODEL_RETRAIN_NO_CACHE", "").lower() not in ("1", "true", "yes")

    if cache_path.is_file() and use_cache and sample_rows == 0:
        logger.info("Loading cached features: %s", cache_path)
        df = pd.read_parquet(cache_path)
    else:
        if not csv_path.is_file():
            raise FileNotFoundError(f"PaySim CSV required for training: {csv_path}")
        logger.info("Loading CSV: %s", csv_path)
        raw = pd.read_csv(csv_path)
        if sample_rows > 0:
            raw = raw.head(sample_rows)
            logger.info("Limited to %s rows (MODEL_RETRAIN_SAMPLE_ROWS)", sample_rows)
        df = transform_paysim_dataframe(raw, fraud_types_only=True)
        if sample_rows == 0:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache_path, index=False)
            logger.info("Cached features to %s", cache_path)

    csv_hash = file_sha256(csv_path) if csv_path.is_file() else None
    tune = os.getenv("MODEL_RETRAIN_TUNE", "").lower() in ("1", "true", "yes")

    bundle = train_and_export(
        df,
        staging,
        paysim_csv_sha256=csv_hash,
        tune=tune,
        tune_n_iter=int(os.getenv("MODEL_RETRAIN_TUNE_N_ITER", "10")),
        max_train_rows=int(os.getenv("MODEL_RETRAIN_MAX_TRAIN_ROWS", "500000") or "500000"),
        imbalance_strategy=os.getenv("MODEL_RETRAIN_IMBALANCE_STRATEGY", "undersample"),
        fraud_types_only=True,
    )

    test_metrics = (bundle.get("metrics") or {}).get("test") or {}
    sidecar = classifier_metrics_sidecar_path(staging)
    return {
        "staging_path": str(staging),
        "metrics_sidecar": str(sidecar),
        "model_version": bundle.get("model_version"),
        "test_pr_auc": test_metrics.get("pr_auc"),
        "test_roc_auc": test_metrics.get("roc_auc"),
        "test_f1": test_metrics.get("f1"),
        "training_rows": bundle.get("training_rows"),
        "trained_at": bundle.get("trained_at"),
    }


def run_anomaly_training() -> dict[str, Any]:
    """Train IsolationForest to staging path."""
    from shared.anomaly_training import train_anomaly_model

    staging = anomaly_staging_path()
    staging.parent.mkdir(parents=True, exist_ok=True)
    return train_anomaly_model(staging)


def evaluate_candidates(
    *,
    candidate_test_pr_auc: float | None = None,
) -> dict[str, Any]:
    """Compare staging vs production; decide promotion (classifier uses test PR-AUC).

    Uses ``.metrics.json`` sidecars when present so production bundles trained with a
    different XGBoost version are not loaded in Airflow.
    """
    staging_clf = classifier_staging_path()
    prod_clf = classifier_production_path()
    staging_anom = anomaly_staging_path()

    min_delta = float(os.getenv("MODEL_RETRAIN_MIN_PR_AUC_DELTA", "0.0"))

    candidate_pr = candidate_test_pr_auc
    if candidate_pr is None:
        candidate_pr = read_test_pr_auc(staging_clf)
    if candidate_pr is None:
        raise FileNotFoundError(
            f"Classifier staging missing test PR-AUC: {staging_clf} "
            f"(expected {classifier_metrics_sidecar_path(staging_clf).name})"
        )

    production_pr: float | None = None
    if prod_clf.is_file():
        production_pr = read_test_pr_auc(prod_clf)

    if not prod_clf.is_file():
        promote_classifier = True
        reason = "no_production_classifier"
    elif production_pr is None:
        promote_classifier = False
        reason = "production_metrics_unavailable"
        logger.warning(
            "Skipping classifier promotion: cannot read production metrics for %s. "
            "Export sidecar with: python scripts/export_classifier_metrics.py",
            prod_clf,
        )
    elif candidate_pr >= production_pr + min_delta:
        promote_classifier = True
        reason = "candidate_improved"
    else:
        promote_classifier = False
        reason = "candidate_below_production"

    promote_anomaly = staging_anom.is_file()
    if not promote_anomaly:
        raise FileNotFoundError(f"Anomaly staging model missing: {staging_anom}")

    return {
        "candidate_test_pr_auc": candidate_pr,
        "production_test_pr_auc": production_pr,
        "min_pr_auc_delta": min_delta,
        "promote_classifier": promote_classifier,
        "promote_classifier_reason": reason,
        "promote_anomaly": promote_anomaly,
        "promote_anomaly_reason": "staging_trained_ok",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def promote_models(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Copy staging artifacts to production paths when evaluation allows."""
    promoted: list[str] = []
    skipped: list[str] = []

    if evaluation.get("promote_classifier"):
        src = classifier_staging_path()
        dst = classifier_production_path()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        sidecar_src = classifier_metrics_sidecar_path(src)
        if sidecar_src.is_file():
            shutil.copy2(sidecar_src, classifier_metrics_sidecar_path(dst))
        promoted.append(str(dst))
        logger.info("Promoted classifier: %s -> %s", src, dst)
    else:
        skipped.append("classifier")

    if evaluation.get("promote_anomaly"):
        src = anomaly_staging_path()
        dst = anomaly_production_path()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        promoted.append(str(dst))
        logger.info("Promoted anomaly: %s -> %s", src, dst)
    else:
        skipped.append("anomaly")

    return {
        "promoted_paths": promoted,
        "skipped": skipped,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }


def record_retrain_manifest(
    *,
    data_check: dict[str, Any],
    classifier_train: dict[str, Any],
    anomaly_train: dict[str, Any],
    evaluation: dict[str, Any],
    promotion: dict[str, Any],
    dag_run_id: str | None = None,
) -> dict[str, Any]:
    """Persist last retrain summary for ops / consumer version hints."""
    manifest = {
        "dag_run_id": dag_run_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "data_check": data_check,
        "classifier_train": classifier_train,
        "anomaly_train": anomaly_train,
        "evaluation": evaluation,
        "promotion": promotion,
        "production_classifier": str(classifier_production_path()),
        "production_anomaly": str(anomaly_production_path()),
        "model_version_hint": os.getenv("MODEL_VERSION", "anomaly_v1"),
        "note": "Restart fraud consumer to reload promoted joblib bundles.",
    }
    path = retrain_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Wrote retrain manifest: %s", path)
    return {"manifest_path": str(path), "promoted": promotion.get("promoted_paths", [])}

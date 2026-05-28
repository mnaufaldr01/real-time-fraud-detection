"""Metrics sidecars for classifier bundles (compare without loading XGBoost)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)


def classifier_metrics_sidecar_path(model_path: Path) -> Path:
    return model_path.with_name(f"{model_path.stem}.metrics.json")


def write_classifier_metrics_sidecar(model_path: Path, metrics: dict[str, Any]) -> Path:
    """Persist test/val metrics next to joblib for cross-environment promotion checks."""
    test = (metrics or {}).get("test") or {}
    sidecar = classifier_metrics_sidecar_path(model_path)
    payload = {
        "test_pr_auc": test.get("pr_auc"),
        "test_roc_auc": test.get("roc_auc"),
        "test_f1": test.get("f1"),
        "threshold_mode": metrics.get("threshold_mode"),
        "model_path": str(model_path),
    }
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sidecar


def read_test_pr_auc(model_path: Path) -> float | None:
    """Read test PR-AUC from sidecar, else from joblib metrics (may fail across XGBoost versions)."""
    sidecar = classifier_metrics_sidecar_path(model_path)
    if sidecar.is_file():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            pr = data.get("test_pr_auc")
            if pr is not None:
                return float(pr)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Invalid metrics sidecar %s: %s", sidecar, exc)

    if not model_path.is_file():
        return None

    try:
        bundle = joblib.load(model_path)
    except Exception as exc:
        logger.warning(
            "Could not load classifier bundle %s (%s). "
            "Add %s via training or scripts/export_classifier_metrics.py.",
            model_path,
            exc,
            sidecar.name,
        )
        return None

    test_metrics = (bundle.get("metrics") or {}).get("test") or {}
    pr_auc = test_metrics.get("pr_auc")
    return float(pr_auc) if pr_auc is not None else None

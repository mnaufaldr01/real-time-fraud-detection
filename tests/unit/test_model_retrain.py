"""Unit tests for weekly model retrain helpers."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pytest

from shared import model_retrain as mr
from shared.model_metrics import write_classifier_metrics_sidecar


def _write_classifier_bundle(path: Path, pr_auc: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = {"test": {"pr_auc": pr_auc, "roc_auc": 0.9, "f1": 0.5}}
    joblib.dump(
        {
            "metrics": metrics,
            "model_version": "test",
        },
        path,
    )
    write_classifier_metrics_sidecar(path, metrics)


def test_check_training_data_requires_csv_or_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_RETRAIN_ROOT", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        mr.check_training_data()

    cache = mr.feature_cache_path()
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"")
    result = mr.check_training_data()
    assert result["cache_present"] is True


def test_evaluate_promotes_when_no_production(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_RETRAIN_ROOT", str(tmp_path))
    staging = mr.classifier_staging_path()
    _write_classifier_bundle(staging, pr_auc=0.42)
    (mr.anomaly_staging_path()).parent.mkdir(parents=True, exist_ok=True)
    mr.anomaly_staging_path().write_bytes(b"stub")

    result = mr.evaluate_candidates()
    assert result["promote_classifier"] is True
    assert result["promote_classifier_reason"] == "no_production_classifier"
    assert result["promote_anomaly"] is True


def test_evaluate_skips_classifier_when_worse(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_RETRAIN_ROOT", str(tmp_path))
    _write_classifier_bundle(mr.classifier_staging_path(), pr_auc=0.40)
    _write_classifier_bundle(mr.classifier_production_path(), pr_auc=0.50)
    mr.anomaly_staging_path().parent.mkdir(parents=True, exist_ok=True)
    mr.anomaly_staging_path().write_text("x")

    result = mr.evaluate_candidates()
    assert result["promote_classifier"] is False
    assert result["promote_anomaly"] is True


def test_evaluate_skips_when_production_metrics_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_RETRAIN_ROOT", str(tmp_path))
    _write_classifier_bundle(mr.classifier_staging_path(), pr_auc=0.55)
    prod = mr.classifier_production_path()
    prod.parent.mkdir(parents=True, exist_ok=True)
    prod.write_bytes(b"not-a-valid-bundle")
    mr.anomaly_staging_path().parent.mkdir(parents=True, exist_ok=True)
    mr.anomaly_staging_path().write_text("x")

    result = mr.evaluate_candidates(candidate_test_pr_auc=0.55)
    assert result["promote_classifier"] is False
    assert result["promote_classifier_reason"] == "production_metrics_unavailable"


def test_promote_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_RETRAIN_ROOT", str(tmp_path))
    _write_classifier_bundle(mr.classifier_staging_path(), pr_auc=0.9)
    mr.anomaly_staging_path().parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"trained_at": "t"}, mr.anomaly_staging_path())

    evaluation = {"promote_classifier": True, "promote_anomaly": True}
    promotion = mr.promote_models(evaluation)
    assert mr.classifier_production_path().is_file()
    assert mr.anomaly_production_path().is_file()

    manifest = mr.record_retrain_manifest(
        data_check={"csv_present": False},
        classifier_train={"test_pr_auc": 0.9},
        anomaly_train={"training_rows": 5000},
        evaluation=evaluation,
        promotion=promotion,
        dag_run_id="test_run",
    )
    data = json.loads(mr.retrain_manifest_path().read_text(encoding="utf-8"))
    assert data["dag_run_id"] == "test_run"
    assert manifest["manifest_path"] == str(mr.retrain_manifest_path())

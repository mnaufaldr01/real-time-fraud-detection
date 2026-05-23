"""Supervised fraud classifier (XGBoost) scoring for bank-transfer transactions."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from consumer.config import config
from shared.schema import PaymentMethod, TransactionEvent

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_bundle: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClassifierThresholds:
    threshold_low: float
    threshold_high: float
    best_threshold: float


@dataclass(frozen=True)
class ClassifierConfig:
    model_version: str
    feature_columns: list[str]
    categorical_features: list[str]
    thresholds: ClassifierThresholds


def _load_bundle() -> dict[str, Any] | None:
    global _bundle
    if _bundle is not None:
        return _bundle
    path = config.classifier_model_path
    if not path.exists():
        logger.info("No classifier bundle at %s — tier scoring uses rules/anomaly only", path)
        return None
    try:
        import joblib

        _bundle = joblib.load(path)
        logger.info("Loaded fraud classifier from %s", path)
        return _bundle
    except Exception as exc:
        logger.warning("Failed to load classifier bundle: %s", exc)
        return None


def get_classifier_config() -> ClassifierConfig | None:
    """Load tier thresholds and feature schema from the training bundle."""
    bundle = _load_bundle()
    if bundle is None:
        return None

    best = float(bundle["best_threshold"])
    t_low = bundle.get("threshold_low")
    t_high = bundle.get("threshold_high")
    if t_low is None or t_high is None:
        metrics = bundle.get("metrics") or {}
        t_low = metrics.get("threshold_low", best * 0.5)
        t_high = metrics.get("threshold_high", best)
        logger.warning(
            "Bundle missing threshold_low/high; using fallbacks t_low=%s t_high=%s",
            t_low,
            t_high,
        )

    return ClassifierConfig(
        model_version=str(bundle.get("model_version", "xgboost_classifier")),
        feature_columns=list(bundle["feature_columns"]),
        categorical_features=list(bundle.get("categorical_features", [])),
        thresholds=ClassifierThresholds(
            threshold_low=float(t_low),
            threshold_high=float(t_high),
            best_threshold=best,
        ),
    )


def is_ml_scoring_scope(event: TransactionEvent) -> bool:
    """XGBoost v1 is trained on PaySim TRANSFER/CASH_OUT → bank_transfer scope."""
    return event.payment_method == PaymentMethod.BANK_TRANSFER


def build_classifier_row(
    event: TransactionEvent,
    *,
    amount_usd: float,
    feature_columns: list[str],
    category_encoder: dict[str, int],
    categorical_features: list[str],
) -> pd.DataFrame:
    """Build one inference row aligned with analysis/paysim_training features."""
    from analysis.paysim_training import (
        is_cash_out_from_merchant_category,
        step_from_timestamp,
    )

    ts = event.timestamp
    row: dict[str, Any] = {
        "amount_usd": round(float(amount_usd), 2),
        "hour_of_day": ts.hour,
        "day_of_week": ts.weekday(),
        "step": step_from_timestamp(ts),
        "is_cash_out": is_cash_out_from_merchant_category(event.merchant_category),
        "merchant_category_encoded": category_encoder.get(event.merchant_category, -1),
        "payment_method": event.payment_method.value,
        "currency": event.currency.upper(),
        "country": event.country.upper(),
    }
    frame = pd.DataFrame([{col: row[col] for col in feature_columns}])
    for col in categorical_features:
        if col in frame.columns:
            frame[col] = frame[col].astype("category")
    return frame


def predict_fraud_probability(
    event: TransactionEvent,
    *,
    amount_usd: float,
) -> Optional[float]:
    """Return fraud probability for in-scope events, else None."""
    if not is_ml_scoring_scope(event):
        return None

    bundle = _load_bundle()
    if bundle is None:
        return None

    model = bundle["model"]
    feature_columns = list(bundle["feature_columns"])
    categorical_features = list(bundle.get("categorical_features", []))
    category_encoder = bundle.get("category_encoder") or {}

    row = build_classifier_row(
        event,
        amount_usd=amount_usd,
        feature_columns=feature_columns,
        category_encoder=category_encoder,
        categorical_features=categorical_features,
    )
    prob = float(model.predict_proba(row)[0, 1])
    return prob

"""Anomaly scoring: z-score baseline with optional IsolationForest model."""

import logging
from typing import Optional

import numpy as np

from consumer.config import MODEL_PATH, config
from shared.schema import TransactionEvent

logger = logging.getLogger(__name__)

_model = None
_category_encoder: Optional[dict] = None


def _load_model():
    global _model, _category_encoder
    if _model is not None:
        return
    if MODEL_PATH.exists():
        try:
            import joblib

            bundle = joblib.load(MODEL_PATH)
            _model = bundle["model"]
            _category_encoder = bundle.get("category_encoder", {})
            logger.info("Loaded IsolationForest model from %s", MODEL_PATH)
        except Exception as exc:
            logger.warning("Failed to load model: %s — falling back to z-score", exc)
    else:
        logger.info("No model file at %s — using z-score only", MODEL_PATH)


def z_score_anomaly(amount: float, user_mean: Optional[float], user_std: Optional[float]) -> float:
    """Convert z-score to 0-100 anomaly score."""
    if user_mean is None or user_std is None or user_std < 1e-6:
        global_mean = config.global_amount_p95 / 2
        global_std = config.global_amount_p95 / 3
        z = abs(amount - global_mean) / global_std
    else:
        z = abs(amount - user_mean) / user_std

    # Map z-score to 0-100: z=0 -> 0, z>=4 -> 100
    score = min(z / 4.0 * 100, 100.0)
    return round(score, 2)


def isolation_forest_score(event: TransactionEvent, amount_usd: float) -> Optional[float]:
    """Score using trained IsolationForest if available."""
    _load_model()
    if _model is None:
        return None

    hour = event.timestamp.hour
    cat_encoded = _category_encoder.get(event.merchant_category, -1) if _category_encoder else -1
    features = np.array([[amount_usd, hour, cat_encoded]])

    raw = _model.decision_function(features)[0]
    # decision_function: lower = more anomalous; map to 0-100
    score = max(0.0, min(100.0, (0.5 - raw) * 100))
    return round(score, 2)


def compute_anomaly_score(
    event: TransactionEvent,
    user_mean: Optional[float] = None,
    user_std: Optional[float] = None,
    *,
    amount_usd: float,
) -> float:
    """Combine z-score and optional ML model (max of both)."""
    zscore = z_score_anomaly(amount_usd, user_mean, user_std)
    ml_score = isolation_forest_score(event, amount_usd)

    if ml_score is not None:
        return max(zscore, ml_score)
    return zscore

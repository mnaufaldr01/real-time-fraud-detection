"""IsolationForest training for consumer anomaly scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

MERCHANT_CATEGORIES = [
    "5411",
    "5812",
    "5912",
    "4121",
    "5999",
    "5541",
    "6011",
    "7011",
    "7832",
    "7995",
]


def generate_training_data(n: int = 5000) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(42)
    category_encoder = {cat: i for i, cat in enumerate(MERCHANT_CATEGORIES)}

    amounts = rng.lognormal(3.5, 0.8, n)
    hours = rng.integers(0, 24, n)
    cats = rng.integers(0, len(MERCHANT_CATEGORIES), n)

    X = np.column_stack([amounts, hours, cats])
    return X, category_encoder


def train_anomaly_model(model_path: Path) -> dict:
    """Fit IsolationForest and write joblib bundle."""
    X, category_encoder = generate_training_data()
    model = IsolationForest(n_estimators=100, contamination=0.03, random_state=42)
    model.fit(X)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    trained_at = datetime.now(timezone.utc).isoformat()
    joblib.dump(
        {
            "model": model,
            "category_encoder": category_encoder,
            "trained_at": trained_at,
            "features": ["amount", "hour_of_day", "merchant_category_encoded"],
        },
        model_path,
    )
    return {"model_path": str(model_path), "trained_at": trained_at, "training_rows": len(X)}

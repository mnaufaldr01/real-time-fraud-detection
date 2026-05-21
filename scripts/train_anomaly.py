"""Offline IsolationForest training on synthetic sample."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "anomaly_v1.joblib"

MERCHANT_CATEGORIES = [
    "5411", "5812", "5912", "4121", "5999", "5541", "6011", "7011", "7832", "7995"
]


def generate_training_data(n: int = 5000) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(42)
    category_encoder = {cat: i for i, cat in enumerate(MERCHANT_CATEGORIES)}

    amounts = rng.lognormal(3.5, 0.8, n)
    hours = rng.integers(0, 24, n)
    cats = rng.integers(0, len(MERCHANT_CATEGORIES), n)

    X = np.column_stack([amounts, hours, cats])
    return X, category_encoder


def main():
    X, category_encoder = generate_training_data()
    model = IsolationForest(n_estimators=100, contamination=0.03, random_state=42)
    model.fit(X)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "category_encoder": category_encoder,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "features": ["amount", "hour_of_day", "merchant_category_encoded"],
        },
        MODEL_PATH,
    )
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()

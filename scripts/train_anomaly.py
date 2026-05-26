"""Offline IsolationForest training on synthetic sample."""

from pathlib import Path

from shared.anomaly_training import train_anomaly_model

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "anomaly_v1.joblib"


def main():
    train_anomaly_model(MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()

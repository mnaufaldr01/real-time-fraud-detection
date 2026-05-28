"""Write .metrics.json sidecar for an existing classifier joblib (no full retrain)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_ROOT / "models" / "fraud_classifier_v1.joblib"


def main() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    import joblib

    from shared.model_metrics import write_classifier_metrics_sidecar

    parser = argparse.ArgumentParser(description="Export classifier metrics sidecar from joblib")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()

    if not args.model.is_file():
        raise FileNotFoundError(f"Model not found: {args.model}")

    bundle = joblib.load(args.model)
    metrics = bundle.get("metrics")
    if not metrics:
        raise ValueError(f"Bundle has no metrics: {args.model}")

    sidecar = write_classifier_metrics_sidecar(args.model, metrics)
    test = metrics.get("test") or {}
    print(f"Wrote {sidecar} (test_pr_auc={test.get('pr_auc')})")


if __name__ == "__main__":
    main()

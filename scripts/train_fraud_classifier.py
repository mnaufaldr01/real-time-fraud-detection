"""Train supervised fraud classifier from PaySim CSV (pipeline-aligned features)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.paysim_training import (
    add_history_features,
    file_sha256,
    train_and_export,
    transform_paysim_dataframe,
)

DEFAULT_CSV = PROJECT_ROOT / "producer" / "sample_dataset" / "PS_20174392719_1491204439457_log.csv"
DEFAULT_CACHE = PROJECT_ROOT / "analysis" / "cache" / "paysim_transformed_transfer_cashout.parquet"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "fraud_classifier_v1.joblib"


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PaySim fraud classifier")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--sample-rows", type=int, default=None, help="Limit rows for quick runs")
    parser.add_argument("--no-cache", action="store_true", help="Rebuild feature parquet")
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Include PAYMENT/DEBIT/CASH_IN rows (default: TRANSFER+CASH_OUT only)",
    )
    parser.add_argument(
        "--with-history",
        action="store_true",
        help="Add slow causal user-history features (v2)",
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run RandomizedSearchCV before final XGBoost training",
    )
    parser.add_argument("--tune-n-iter", type=int, default=15)
    parser.add_argument(
        "--fraud-weight-multiplier",
        type=float,
        default=1.0,
        help="Multiplier on scale_pos_weight (target_rate / train_prior modes only)",
    )
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=2_000_000,
        help="Recency window: max chronological train rows before val (0 = no limit)",
    )
    parser.add_argument(
        "--imbalance-strategy",
        choices=("undersample", "target_rate", "train_prior"),
        default="undersample",
        help="How to handle train/test fraud-rate drift",
    )
    parser.add_argument(
        "--target-fraud-rate",
        type=float,
        default=None,
        help="Deployment fraud rate for weights/sampling (default: infer from val+test)",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Train with CUDA GPU when available (falls back to CPU)",
    )
    parser.add_argument(
        "--min-recall",
        type=float,
        default=0.70,
        help="Used when --threshold-mode=recall",
    )
    parser.add_argument(
        "--min-precision",
        type=float,
        default=0.50,
        help="Used when --threshold-mode=precision (reduces false alarms)",
    )
    parser.add_argument(
        "--threshold-mode",
        choices=("precision", "recall", "manual"),
        default="precision",
        help="How to set the production probability cutoff on validation data",
    )
    parser.add_argument(
        "--manual-threshold",
        type=float,
        default=None,
        help="Fixed cutoff when --threshold-mode=manual (e.g. 0.85)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        raise FileNotFoundError(f"Missing PaySim CSV: {args.csv}")

    if args.cache.exists() and not args.no_cache and args.sample_rows is None:
        print(f"Loading cached features: {args.cache}")
        df = pd.read_parquet(args.cache)
    else:
        print(f"Loading CSV: {args.csv}")
        raw = pd.read_csv(args.csv)
        if args.sample_rows:
            raw = raw.head(args.sample_rows)
        print(f"Transforming {len(raw):,} rows...", flush=True)
        df = transform_paysim_dataframe(raw, fraud_types_only=not args.all_types)
        if args.with_history:
            print(f"Engineering history features on {len(df):,} rows...", flush=True)
            df = add_history_features(df)
        if args.sample_rows is None:
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(args.cache, index=False)
            print(f"Cached features to {args.cache}")

    csv_hash = file_sha256(args.csv) if args.csv.exists() else None
    train_and_export(
        df,
        args.model,
        include_history=args.with_history,
        paysim_csv_sha256=csv_hash,
        tune=args.tune,
        tune_n_iter=args.tune_n_iter,
        fraud_weight_multiplier=args.fraud_weight_multiplier,
        use_gpu=args.gpu,
        min_recall=args.min_recall,
        threshold_mode=args.threshold_mode,
        min_precision=args.min_precision,
        manual_threshold=args.manual_threshold,
        max_train_rows=args.max_train_rows or None,
        imbalance_strategy=args.imbalance_strategy,
        target_fraud_rate=args.target_fraud_rate,
        fraud_types_only=not args.all_types,
    )


if __name__ == "__main__":
    main()

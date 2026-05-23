"""PaySim → pipeline-aligned features and supervised fraud model training."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
import xgboost as xgb
from xgboost import XGBClassifier

from shared.fx import (
    BASE_CURRENCY,
    DEFAULT_FX_RATES,
    assign_currency,
    country_for_currency,
    to_usd,
)
from shared.paysim_transform import BASE_TIME, TYPE_TO_MCC, TYPE_TO_PAYMENT, transform_row

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
    "6012",
]

CATEGORY_ENCODER = {cat: i for i, cat in enumerate(MERCHANT_CATEGORIES)}

# v1: event + FX only (no Postgres history) — matches Kafka payload at scoring time
STATIC_NUMERIC_FEATURES = ["amount_usd", "hour_of_day", "day_of_week"]
STATIC_CATEGORICAL_FEATURES = [
    "merchant_category_encoded",
    "payment_method",
    "currency",
    "country",
]

# v2 (optional later): causal user history from consumer/sink.py
HISTORY_NUMERIC_FEATURES = [
    "tx_count_1h",
    "user_mean",
    "user_std",
    "amount_p95",
    "amount_p99",
    "seen_merchants_count",
    "is_new_merchant",
    "amount_to_user_mean_ratio",
]

HISTORY_FEATURES_REQUIRED = [
    "tx_count_1h",
    "user_mean",
    "user_std",
    "amount_p95",
    "amount_p99",
    "seen_merchants_count",
    "is_new_merchant",
]

ROLLING_QUANTILE_WINDOW = 500


def feature_columns(include_history: bool = False) -> list[str]:
    numeric = list(STATIC_NUMERIC_FEATURES)
    if include_history:
        numeric.extend(HISTORY_NUMERIC_FEATURES)
    return numeric + list(STATIC_CATEGORICAL_FEATURES)


def numeric_features(include_history: bool = False) -> list[str]:
    cols = list(STATIC_NUMERIC_FEATURES)
    if include_history:
        cols.extend(HISTORY_NUMERIC_FEATURES)
    return cols


def categorical_features() -> list[str]:
    return list(STATIC_CATEGORICAL_FEATURES)


# Default training path (v1 static)
FEATURE_COLUMNS = feature_columns(include_history=False)
NUMERIC_FEATURES = numeric_features(include_history=False)
CATEGORICAL_FEATURES = categorical_features()


def _vectorized_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized PaySim → pipeline event fields (matches transform_row)."""
    work = df.loc[df["amount"].astype(float) > 0].copy()
    work["user_id"] = work["nameOrig"].astype(str)
    work["merchant_id"] = work["nameDest"].astype(str)
    work["step"] = work["step"].astype(int)
    work["timestamp"] = BASE_TIME + pd.to_timedelta(work["step"], unit="h")
    tx_type = work["type"].astype(str)
    work["payment_method"] = tx_type.map(TYPE_TO_PAYMENT).fillna("card")
    work["merchant_category"] = tx_type.map(TYPE_TO_MCC).fillna("5999")
    work["currency"] = work["user_id"].map(assign_currency)
    work["country"] = [
        country_for_currency(c, u) for c, u in zip(work["currency"], work["user_id"])
    ]
    work["ip_country"] = work["country"]
    amount_ref = work["amount"].astype(float)
    work["amount_local"] = amount_ref.round(2)
    for code, rate in DEFAULT_FX_RATES.items():
        if code == BASE_CURRENCY:
            continue
        mask = work["currency"] == code
        if not mask.any():
            continue
        local = amount_ref[mask] / rate
        work.loc[mask, "amount_local"] = local.round(0) if code == "IDR" else local.round(2)
    rates = work["currency"].map(DEFAULT_FX_RATES)
    work["amount_usd"] = (work["amount_local"] * rates).round(2)
    work["isFraud"] = work["isFraud"].astype(int)
    work["hour_of_day"] = work["timestamp"].dt.hour
    work["day_of_week"] = work["timestamp"].dt.dayofweek
    work["merchant_category_encoded"] = (
        work["merchant_category"].map(CATEGORY_ENCODER).fillna(-1).astype(int)
    )
    return work


def transform_paysim_dataframe(
    df: pd.DataFrame,
    *,
    sample_rows: int | None = None,
    validate_sample: int = 100,
) -> pd.DataFrame:
    """Transform raw PaySim CSV rows to pipeline-aligned columns."""
    if sample_rows is not None:
        df = df.head(sample_rows)

    transformed = _vectorized_transform(df)

    if validate_sample > 0:
        _assert_matches_transform_row(df, transformed, n=validate_sample)

    return transformed


def _assert_matches_transform_row(
    raw: pd.DataFrame,
    transformed: pd.DataFrame,
    n: int = 100,
) -> None:
    """Spot-check vectorized path against shared.paysim_transform.transform_row."""
    raw_pos = raw.loc[raw["amount"].astype(float) > 0].head(n)
    for _, row in raw_pos.iterrows():
        expected = transform_row(row.to_dict())
        if expected is None:
            continue
        user_id = str(row["nameOrig"])
        match = transformed.loc[transformed["user_id"] == user_id].iloc[0]
        assert match["merchant_id"] == expected["merchant_id"]
        assert match["payment_method"] == expected["payment_method"]
        assert match["merchant_category"] == expected["merchant_category"]
        assert match["currency"] == expected["currency"]
        assert match["country"] == expected["country"]
        assert abs(match["amount_local"] - expected["amount"]) < 0.02
        usd = to_usd(expected["amount"], expected["currency"])
        assert abs(match["amount_usd"] - usd) < 0.02


def add_history_features(df: pd.DataFrame) -> pd.DataFrame:
    """Causal user-history features aligned with consumer/sink.py semantics."""
    work = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    g = work.groupby("user_id", sort=False)

    tx_raw = (
        g.rolling("1h", on="timestamp", closed="left")["amount_usd"]
        .count()
        .to_numpy()
    )
    work["tx_count_1h"] = tx_raw
    work["tx_count_1h"] = g["tx_count_1h"].shift(1).fillna(0).astype(float)

    prior_amount = g["amount_usd"].shift(1)
    work["user_mean"] = prior_amount.groupby(work["user_id"], sort=False).transform(
        lambda s: s.expanding(min_periods=1).mean()
    )
    work["user_std"] = prior_amount.groupby(work["user_id"], sort=False).transform(
        lambda s: s.expanding(min_periods=2).std()
    )

    # Rolling max over prior txs approximates P99; P95 scaled (quantile() is too slow at 6M+ rows)
    prior_max = g["amount_usd"].transform(
        lambda s: s.shift(1).rolling(ROLLING_QUANTILE_WINDOW, min_periods=1).max()
    )
    work["amount_p99"] = prior_max
    work["amount_p95"] = prior_max * 0.92

    first_merchant = g["merchant_id"].transform(lambda s: s.groupby(s, sort=False).cumcount() == 0)
    work["seen_merchants_count"] = (
        first_merchant.groupby(work["user_id"], sort=False).transform("cumsum").shift(1).fillna(0)
    )
    work["is_new_merchant"] = first_merchant.astype(int)

    work["amount_to_user_mean_ratio"] = work["amount_usd"] / work["user_mean"]
    work.loc[~np.isfinite(work["amount_to_user_mean_ratio"]), "amount_to_user_mean_ratio"] = np.nan

    return work


def time_split(
    df: pd.DataFrame,
    *,
    train_frac: float = 0.7,
    val_frac: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    max_step = int(df["step"].max())
    train_end = int(max_step * train_frac)
    val_end = int(max_step * (train_frac + val_frac))

    train = df[df["step"] < train_end]
    val = df[(df["step"] >= train_end) & (df["step"] < val_end)]
    test = df[df["step"] >= val_end]
    return train, val, test


def prepare_xy(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    cols = columns or FEATURE_COLUMNS
    x = df[cols].copy()
    cat_cols = [c for c in cols if c in STATIC_CATEGORICAL_FEATURES]
    for col in cat_cols:
        x[col] = x[col].astype("category")
    y = df["isFraud"].astype(int)
    return x, y


_DEVICE_CACHE: dict[bool, str] = {}


def resolve_xgb_device(use_gpu: bool = False) -> str:
    """Return 'cuda' when GPU training is requested and available, else 'cpu'."""
    if use_gpu in _DEVICE_CACHE:
        return _DEVICE_CACHE[use_gpu]
    if not use_gpu:
        _DEVICE_CACHE[use_gpu] = "cpu"
        return "cpu"
    if not xgb.build_info().get("USE_CUDA", False):
        print("XGBoost was built without CUDA — using CPU.")
        _DEVICE_CACHE[use_gpu] = "cpu"
        return "cpu"
    try:
        probe = XGBClassifier(
            n_estimators=1,
            device="cuda",
            tree_method="hist",
            n_jobs=1,
        )
        x_probe = np.array([[0.0], [1.0]], dtype=np.float32)
        y_probe = np.array([0, 1], dtype=int)
        probe.fit(x_probe, y_probe)
        print("XGBoost GPU (CUDA) available — training on GPU.")
        _DEVICE_CACHE[use_gpu] = "cuda"
        return "cuda"
    except Exception as exc:
        print(f"CUDA unavailable ({exc}) — falling back to CPU.")
        _DEVICE_CACHE[use_gpu] = "cpu"
        return "cpu"


def scale_pos_weight_from_labels(
    y: pd.Series | np.ndarray,
    *,
    multiplier: float = 1.0,
) -> float:
    """XGBoost weight for the positive (fraud) class: (legit/fraud) * multiplier."""
    y_arr = np.asarray(y)
    positives = int(y_arr.sum())
    negatives = int(len(y_arr) - positives)
    base = negatives / max(positives, 1)
    return base * multiplier


def build_classifier(
    columns: list[str] | None = None,
    *,
    scale_pos_weight: float = 1.0,
    use_gpu: bool = False,
    **overrides: Any,
) -> XGBClassifier:
    device = resolve_xgb_device(use_gpu)
    params: dict[str, Any] = {
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 8,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "enable_categorical": True,
        "tree_method": "hist",
        "eval_metric": "aucpr",
        "early_stopping_rounds": 30,
        "scale_pos_weight": scale_pos_weight,
        "random_state": 42,
        "device": device,
        "n_jobs": 1 if device == "cuda" else -1,
    }
    params.update(overrides)
    params["device"] = device
    if device == "cuda":
        params["n_jobs"] = 1
    return XGBClassifier(**params)


def training_progress_callbacks(*, period: int = 10) -> list[Any]:
    """XGBoost callbacks that print train/val metrics every `period` boosting rounds."""
    from xgboost.callback import EvaluationMonitor

    return [EvaluationMonitor(period=period)]


def tune_classifier(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    *,
    n_iter: int = 15,
    sample_frac: float = 0.25,
    cv: int = 3,
    random_state: int = 42,
    fraud_weight_multiplier: float = 1.0,
    use_gpu: bool = False,
    verbose: int = 2,
) -> tuple[dict[str, Any], float]:
    """Random search for XGBoost hyperparameters (subsampled for speed)."""
    if sample_frac < 1.0:
        n = max(10_000, int(len(x_train) * sample_frac))
        n = min(n, len(x_train))
        rng = np.random.default_rng(random_state)
        idx = rng.choice(len(x_train), size=n, replace=False)
        x_sub = x_train.iloc[idx]
        y_sub = y_train.iloc[idx]
    else:
        x_sub, y_sub = x_train, y_train

    pos_weight = scale_pos_weight_from_labels(y_sub, multiplier=fraud_weight_multiplier)
    base = build_classifier(
        scale_pos_weight=pos_weight,
        use_gpu=use_gpu,
        n_estimators=200,
        early_stopping_rounds=None,
    )
    param_dist = {
       "max_depth": [6, 8],
        "learning_rate": [0.05, 0.1],
        "min_child_weight": [1, 5],
        "subsample": [0.8, 1.0],
    }
    total_fits = n_iter * cv
    print(
        f"Hyperparameter search: {n_iter} candidates × {cv}-fold CV "
        f"({total_fits} fits, {len(x_sub):,} rows)...",
        flush=True,
    )
    t0 = time.perf_counter()
    # GPU fits must run sequentially; parallel CV jobs would contend for the GPU.
    search = RandomizedSearchCV(
        base,
        param_distributions=param_dist,
        n_iter=n_iter,
        scoring="average_precision",
        cv=cv,
        random_state=random_state,
        n_jobs=1 if use_gpu else -1,
        verbose=verbose,
    )
    search.fit(x_sub, y_sub)
    elapsed = time.perf_counter() - t0
    print(f"Hyperparameter search finished in {elapsed:.1f}s", flush=True)
    return dict(search.best_params_), float(search.best_score_)


def precision_at_top_k(y_true: np.ndarray, y_prob: np.ndarray, k: float = 0.01) -> float:
    n = max(1, int(len(y_prob) * k))
    top_idx = np.argsort(y_prob)[-n:]
    return float(y_true[top_idx].mean())


def find_threshold_for_precision(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_precision: float = 0.80,
) -> tuple[float, float, float]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    best_t, best_p, best_r = 0.5, 0.0, 0.0
    for p, r, t in zip(precisions[:-1], recalls[:-1], thresholds):
        if p >= min_precision and r >= best_r:
            best_t, best_p, best_r = float(t), float(p), float(r)
    if best_p == 0.0:
        idx = int(np.argmax(precisions[:-1]))
        best_t = float(thresholds[idx])
        best_p = float(precisions[idx])
        best_r = float(recalls[idx])
    return best_t, best_p, best_r


def find_threshold_for_recall(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_recall: float = 0.70,
) -> tuple[float, float, float]:
    """Threshold on val that maximizes precision among points with recall >= min_recall."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    best_t, best_p, best_r = 0.5, 0.0, 0.0
    for p, r, t in zip(precisions[:-1], recalls[:-1], thresholds):
        if r >= min_recall and p >= best_p:
            best_t, best_p, best_r = float(t), float(p), float(r)
    if best_r < min_recall:
        idx = int(np.argmax(recalls[:-1]))
        best_t = float(thresholds[idx])
        best_p = float(precisions[idx])
        best_r = float(recalls[idx])
    return best_t, best_p, best_r


def classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    """Full classification metrics + confusion matrix for fraud (positive=1)."""
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])
    n_fraud = int(y_true.sum())
    n_legit = int(len(y_true) - n_fraud)

    return {
        "threshold": float(threshold),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision_at_1pct": precision_at_top_k(y_true, y_prob, 0.01),
        "specificity": float(tn / max(tn + fp, 1)),
        "false_positive_rate": float(fp / max(n_legit, 1)),
        "false_negative_rate": float(fn / max(n_fraud, 1)),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "fraud_caught_pct": float(tp / max(n_fraud, 1)),
        "fraud_missed_pct": float(fn / max(n_fraud, 1)),
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": {"rows": ["legit", "fraud"], "cols": ["pred_legit", "pred_fraud"]},
    }


def print_evaluation_report(
    split_name: str,
    y_true: np.ndarray | pd.Series,
    y_prob: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    """Print confusion matrix and fraud-focused metrics (recall emphasized)."""
    y_arr = np.asarray(y_true, dtype=int)
    m = classification_metrics(y_arr, y_prob, threshold)
    cm = np.array(m["confusion_matrix"])

    print(f"\n{'=' * 60}", flush=True)
    print(f"  {split_name} @ threshold = {threshold:.4f}", flush=True)
    print(f"{'=' * 60}", flush=True)
    print("\nConfusion matrix (rows=actual, cols=predicted):", flush=True)
    print("                 pred_legit  pred_fraud", flush=True)
    print(f"  actual legit   {cm[0, 0]:>10,}  {cm[0, 1]:>10,}", flush=True)
    print(f"  actual fraud   {cm[1, 0]:>10,}  {cm[1, 1]:>10,}", flush=True)

    print("\nRanking metrics (threshold-free):", flush=True)
    print(f"  PR-AUC (average precision): {m['pr_auc']:.4f}", flush=True)
    print(f"  ROC-AUC:                    {m['roc_auc']:.4f}", flush=True)
    print(f"  Precision @ top 1% scores:  {m['precision_at_1pct']:.4f}", flush=True)

    print("\nClassification @ threshold (fraud = positive class):", flush=True)
    print(f"  Recall (fraud caught):      {m['recall']:.4f}  ({m['true_positives']:,} / {int(y_arr.sum()):,} frauds)", flush=True)
    print(f"  Precision (fraud flags OK): {m['precision']:.4f}", flush=True)
    print(f"  F1:                         {m['f1']:.4f}", flush=True)
    print(f"  Specificity (legit correct):{m['specificity']:.4f}", flush=True)
    print(f"  False positive rate:        {m['false_positive_rate']:.4%}  ({m['false_positives']:,} false alarms)", flush=True)
    print(f"  False negative rate:        {m['false_negative_rate']:.4%}  ({m['false_negatives']:,} missed frauds)", flush=True)
    return m


def evaluate_model(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    *,
    threshold: float,
    columns: list[str] | None = None,
    sample_size: int = 50_000,
) -> dict[str, Any]:
    cols = columns or FEATURE_COLUMNS
    y_prob = pipeline.predict_proba(x)[:, 1]
    y_true = y.to_numpy()
    metrics = classification_metrics(y_true, y_prob, threshold)

    if sample_size and len(x) > sample_size:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(x), size=sample_size, replace=False)
        x_sample = x.iloc[idx]
        y_sample = y.iloc[idx]
    else:
        x_sample = x
        y_sample = y

    perm = permutation_importance(
        pipeline,
        x_sample,
        y_sample,
        n_repeats=5,
        random_state=42,
        scoring="average_precision",
        n_jobs=-1,
    )
    metrics["permutation_importance"] = {
        cols[i]: float(perm.importances_mean[i]) for i in range(len(cols))
    }
    return metrics, y_prob


def save_model_bundle(
    pipeline: Pipeline,
    model_path: Path,
    *,
    feature_columns: list[str],
    numeric_columns: list[str],
    categorical_columns: list[str],
    best_threshold: float,
    metrics: dict[str, Any],
    include_history: bool = False,
    classifier_params: dict[str, Any] | None = None,
    scale_pos_weight: float | None = None,
    fraud_weight_multiplier: float | None = None,
    device: str | None = None,
    paysim_csv_sha256: str | None = None,
    training_rows: int | None = None,
) -> dict[str, Any]:
    bundle = {
        "model": pipeline,
        "model_type": "xgboost_classifier",
        "model_version": "ml_v1_static" if not include_history else "ml_v2_history",
        "feature_columns": feature_columns,
        "categorical_features": categorical_columns,
        "numeric_features": numeric_columns,
        "category_encoder": CATEGORY_ENCODER,
        "history_features_required": HISTORY_FEATURES_REQUIRED if include_history else [],
        "include_history": include_history,
        "best_threshold": best_threshold,
        "classifier_params": classifier_params or {},
        "scale_pos_weight": scale_pos_weight,
        "fraud_weight_multiplier": fraud_weight_multiplier,
        "device": device,
        "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": training_rows,
        "paysim_csv_sha256": paysim_csv_sha256,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    print(f"Model saved to {model_path}")
    return bundle


def train_and_export(
    df: pd.DataFrame,
    model_path: Path,
    *,
    include_history: bool = False,
    paysim_csv_sha256: str | None = None,
    tune: bool = False,
    tune_n_iter: int = 15,
    tune_sample_frac: float = 0.25,
    fraud_weight_multiplier: float = 1.0,
    use_gpu: bool = False,
    min_recall: float = 0.70,
) -> dict[str, Any]:
    device = resolve_xgb_device(use_gpu)
    cols = feature_columns(include_history=include_history)
    num_cols = numeric_features(include_history=include_history)
    cat_cols = categorical_features()
    train, val, test = time_split(df)
    for name, part in [("train", train), ("val", val), ("test", test)]:
        rate = part["isFraud"].mean()
        print(f"{name}: rows={len(part):,} fraud_rate={rate:.4%} frauds={part['isFraud'].sum():,}")

    if test["isFraud"].sum() < 50:
        raise ValueError(f"Test split has only {test['isFraud'].sum()} fraud rows; need >= 50")

    x_train, y_train = prepare_xy(train, columns=cols)
    x_val, y_val = prepare_xy(val, columns=cols)
    x_test, y_test = prepare_xy(test, columns=cols)

    pos_weight = scale_pos_weight_from_labels(y_train, multiplier=fraud_weight_multiplier)
    print(
        f"Class imbalance: {y_train.sum():,} fraud / {len(y_train):,} train rows "
        f"({y_train.mean():.4%}) — scale_pos_weight={pos_weight:,.1f} "
        f"(multiplier={fraud_weight_multiplier}x)"
    )
    classifier_params: dict[str, Any] = {}
    if tune:
        print(f"Tuning XGBClassifier on {len(cols)} static features...")
        classifier_params, cv_score = tune_classifier(
            x_train,
            y_train,
            n_iter=tune_n_iter,
            sample_frac=tune_sample_frac,
            fraud_weight_multiplier=fraud_weight_multiplier,
            use_gpu=use_gpu,
        )
        print(f"Best CV PR-AUC={cv_score:.4f} params={classifier_params}")

    clf = build_classifier(
        cols, scale_pos_weight=pos_weight, use_gpu=use_gpu, **classifier_params
    )
    pipeline = Pipeline([("clf", clf)])
    print(
        f"Training XGBClassifier ({len(cols)} features, device={device}, "
        f"scale_pos_weight={pos_weight:,.1f})..."
    )
    pipeline.fit(
        x_train,
        y_train,
        clf__eval_set=[(x_val, y_val)],
        clf__verbose=False,
    )

    val_prob = pipeline.predict_proba(x_val)[:, 1]
    y_val_arr = y_val.to_numpy()
    best_threshold, val_precision, val_recall = find_threshold_for_recall(
        y_val_arr, val_prob, min_recall=min_recall
    )
    print(
        f"Val threshold (recall>={min_recall:.0%}): {best_threshold:.4f} "
        f"precision={val_precision:.4f} recall={val_recall:.4f}",
        flush=True,
    )
    print_evaluation_report("Validation", y_val_arr, val_prob, best_threshold)
    test_prob = pipeline.predict_proba(x_test)[:, 1]
    print_evaluation_report("Test", y_test.to_numpy(), test_prob, best_threshold)

    val_metrics, _ = evaluate_model(
        pipeline, x_val, y_val, threshold=best_threshold, columns=cols
    )
    test_metrics, _ = evaluate_model(
        pipeline, x_test, y_test, threshold=best_threshold, columns=cols
    )

    return save_model_bundle(
        pipeline,
        model_path,
        feature_columns=cols,
        numeric_columns=num_cols,
        categorical_columns=cat_cols,
        best_threshold=best_threshold,
        metrics={
            "val": val_metrics,
            "test": test_metrics,
            "threshold_strategy": f"max_precision_at_recall>={min_recall}",
            "min_recall_target": min_recall,
            "val_precision_at_threshold": val_precision,
            "val_recall_at_threshold": val_recall,
        },
        include_history=include_history,
        classifier_params=classifier_params or None,
        scale_pos_weight=pos_weight,
        fraud_weight_multiplier=fraud_weight_multiplier,
        device=device,
        paysim_csv_sha256=paysim_csv_sha256,
        training_rows=len(train),
    )


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

"""Classifier defaults and tune-metric scorers."""

import numpy as np
import pytest

from analysis.paysim_training import (
    DEFAULT_EARLY_STOPPING_ROUNDS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MIN_CHILD_WEIGHT,
    DEFAULT_N_ESTIMATORS,
    build_classifier,
    recall_at_max_fpr,
    resolve_tune_scorer,
    tune_classifier,
)


def test_build_classifier_defaults():
    clf = build_classifier()
    assert clf.n_estimators == DEFAULT_N_ESTIMATORS
    assert clf.max_depth == DEFAULT_MAX_DEPTH
    assert clf.min_child_weight == DEFAULT_MIN_CHILD_WEIGHT
    assert clf.early_stopping_rounds == DEFAULT_EARLY_STOPPING_ROUNDS


def test_recall_at_max_fpr():
    y = np.array([0, 0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.4, 0.8, 0.9])
    r = recall_at_max_fpr(y, p, max_fpr=0.5)
    assert 0.0 <= r <= 1.0
    assert r >= 0.5


def test_resolve_tune_scorer_names():
    assert resolve_tune_scorer("average_precision") == "average_precision"
    assert hasattr(resolve_tune_scorer("precision_at_top_1pct"), "_score_func")
    assert hasattr(resolve_tune_scorer("recall_at_fpr_05"), "_score_func")


def test_resolve_tune_scorer_unknown():
    with pytest.raises(ValueError, match="Unknown tune metric"):
        resolve_tune_scorer("not_a_metric")


def test_tune_classifier_runs_with_custom_metric():
    rng = np.random.default_rng(0)
    n = 400
    x = rng.normal(size=(n, 3))
    y = (x[:, 0] + rng.normal(scale=0.5, size=n) > 0).astype(int)
    import pandas as pd

    df_x = pd.DataFrame(x, columns=["a", "b", "c"])
    params, score = tune_classifier(
        df_x,
        pd.Series(y),
        n_iter=2,
        sample_frac=1.0,
        cv=2,
        use_gpu=False,
        verbose=0,
        tune_metric="precision_at_top_1pct",
    )
    assert isinstance(params, dict)
    assert "max_depth" in params
    assert 0.0 <= score <= 1.0

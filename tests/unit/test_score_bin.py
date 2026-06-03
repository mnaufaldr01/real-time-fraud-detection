"""Score bin analysis for validation threshold policy."""

import numpy as np

from analysis.paysim_training import (
    print_score_bin_contrast_report,
    print_score_bin_report,
    score_bin_contrast_table,
    score_bin_table,
)


def test_score_bin_table_uniform_bins_fraud_concentration():
    y = np.array([0] * 90 + [1] * 10)
    # High scores get all fraud
    p = np.concatenate([np.linspace(0.05, 0.45, 90), np.linspace(0.55, 0.95, 10)])

    df = score_bin_table(y, p, n_bins=10, binning="uniform")

    assert len(df) == 10
    assert df["frauds"].sum() == 10
    assert df.loc[df["score_min"] >= 0.5, "frauds"].sum() == 10
    # cum_pct is measured from highest scores downward; lowest bin reaches 100%
    assert df["cum_pct_of_all_fraud"].max() == 1.0


def test_score_bin_suggested_action_with_tiers():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.05, 0.25, 0.75, 0.95])

    df = score_bin_table(
        y,
        p,
        n_bins=10,
        binning="uniform",
        threshold_low=0.20,
        threshold_high=0.70,
    )

    assert (df.loc[df["suggested_action"] == "approve", "score_max"] <= 0.20).all()
    assert (df.loc[df["suggested_action"] == "auto_block", "score_min"] >= 0.70).all()


def test_score_bin_contrast_finds_numeric_difference():
    import pandas as pd

    features = pd.DataFrame(
        {
            "amount_usd": [10.0, 12.0, 100.0, 110.0],
            "hour_of_day": [1, 2, 1, 2],
            "day_of_week": [0, 0, 0, 0],
            "step": [1, 1, 1, 1],
            "is_cash_out": [0, 0, 0, 0],
            "merchant_category_encoded": [0, 0, 0, 0],
            "payment_method": ["card", "card", "card", "card"],
            "currency": ["USD", "USD", "USD", "USD"],
            "country": ["US", "US", "US", "US"],
        }
    )
    # Same high-score bin: fraud and legit both present
    y = np.array([0, 1, 0, 1])
    p = np.array([0.85, 0.90, 0.88, 0.92])

    df = score_bin_contrast_table(
        features,
        y,
        p,
        n_bins=2,
        binning="uniform",
        min_frauds=1,
        min_legit=1,
    )
    high = df[(df["score_range"] == "0.5-1.0") & (df["feature"] == "amount_usd")]
    assert not high.empty
    assert float(high.iloc[0]["contrast"]) > 0


def test_print_score_bin_report_returns_dataframe(capsys):
    y = np.array([0, 1])
    p = np.array([0.1, 0.9])
    df = print_score_bin_report("val", y, p, n_bins=2, binning="uniform")
    captured = capsys.readouterr().out
    assert "Score bin analysis" in captured
    assert len(df) >= 1

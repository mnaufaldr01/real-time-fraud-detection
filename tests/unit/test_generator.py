"""Tests for synthetic generator helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from producer.generator import _velocity_burst_timestamps


def test_velocity_burst_timestamps_sub_second_spread():
    base = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    stamps = _velocity_burst_timestamps(base, 8)

    assert len(stamps) == 8
    assert stamps[0] == base

    gaps = [(stamps[i] - stamps[i - 1]).total_seconds() for i in range(1, len(stamps))]
    assert all(0.0 < gap <= 1.75 for gap in gaps)
    assert (stamps[-1] - stamps[0]).total_seconds() <= 5.0
    assert any(gap != int(gap) for gap in gaps)


def test_high_amount_fraud_uses_geo_mismatch_and_profile_range():
    from producer.generator import _high_amount_fraud_transaction
    from shared.synthetic import HIGH_AMOUNT_MERCHANT_PROFILES, reference_amount_usd

    profile = HIGH_AMOUNT_MERCHANT_PROFILES[0]
    txn = _high_amount_fraud_transaction(profile)
    assert txn["merchant_id"] == profile.merchant_id
    assert txn["country"] != txn["ip_country"]
    amount_usd = reference_amount_usd(txn)
    assert profile.min_usd <= amount_usd <= profile.max_usd

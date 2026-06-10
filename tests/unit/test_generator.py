"""Tests for synthetic generator helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from consumer.validate import validate_event
from producer.generator import _velocity_burst_timestamps, generate_malformed


def test_velocity_burst_timestamps_sub_second_spread():
    base = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    stamps = _velocity_burst_timestamps(base, 8)

    assert len(stamps) == 8
    assert stamps[0] == base

    gaps = [(stamps[i] - stamps[i - 1]).total_seconds() for i in range(1, len(stamps))]
    assert all(0.0 < gap <= 1.75 for gap in gaps)
    assert (stamps[-1] - stamps[0]).total_seconds() <= 5.0
    assert any(gap != int(gap) for gap in gaps)


def test_generate_malformed_always_fails_validation():
    for _ in range(30):
        _, value, _ = generate_malformed()
        result = validate_event(value)
        assert result.ok is False
        assert result.error_code in ("INVALID_JSON", "SCHEMA_VALIDATION")


def test_generate_malformed_invalid_json_is_not_parseable():
    for _ in range(20):
        _, value, violation = generate_malformed()
        if violation == "invalid_json":
            with pytest.raises(json.JSONDecodeError):
                json.loads(value.decode("utf-8"))
            return
    pytest.skip("invalid_json not sampled in 20 draws")


def test_high_amount_fraud_uses_geo_mismatch_and_profile_range():
    from producer.generator import _high_amount_fraud_transaction
    from shared.synthetic import HIGH_AMOUNT_MERCHANT_PROFILES, reference_amount_usd

    profile = HIGH_AMOUNT_MERCHANT_PROFILES[0]
    txn = _high_amount_fraud_transaction(profile)
    assert txn["merchant_id"] == profile.merchant_id
    assert txn["country"] != txn["ip_country"]
    amount_usd = reference_amount_usd(txn)
    assert profile.min_usd <= amount_usd <= profile.max_usd

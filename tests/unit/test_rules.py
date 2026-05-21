"""Unit tests for fraud rules."""

import uuid
from datetime import datetime, timezone

import pytest

from consumer.rules import UserStats, evaluate_rules
from shared.schema import PaymentMethod, TransactionEvent


def _event(**kwargs) -> TransactionEvent:
    defaults = {
        "transaction_id": uuid.uuid4(),
        "user_id": "user_001",
        "timestamp": datetime.now(timezone.utc),
        "amount": 50.0,
        "currency": "USD",
        "merchant_id": "m_001",
        "merchant_category": "5411",
        "country": "US",
        "payment_method": PaymentMethod.CARD,
        "ip_country": "US",
    }
    defaults.update(kwargs)
    return TransactionEvent(**defaults)


def test_geo_mismatch_triggers():
    event = _event(country="US", ip_country="RU")
    result = evaluate_rules(event, UserStats())
    assert "GEO_MISMATCH" in result.triggered_rules
    assert result.hard_decline is True


def test_velocity_triggers():
    stats = UserStats(tx_count_1h=6)
    result = evaluate_rules(_event(), stats)
    assert "VELOCITY_1H" in result.triggered_rules
    assert result.hard_decline is True


def test_high_amount_triggers():
    stats = UserStats(amount_p99=100.0)
    event = _event(amount=500.0)
    result = evaluate_rules(event, stats)
    assert "HIGH_AMOUNT" in result.triggered_rules


def test_new_merchant_high_triggers():
    stats = UserStats(amount_p95=100.0, seen_merchants={"m_other"})
    event = _event(merchant_id="m_new", amount=200.0)
    result = evaluate_rules(event, stats)
    assert "NEW_MERCHANT_HIGH" in result.triggered_rules


def test_clean_transaction_no_rules():
    stats = UserStats(tx_count_1h=1, amount_p99=1000.0, seen_merchants={"m_001"})
    result = evaluate_rules(_event(amount=50.0), stats)
    assert result.triggered_rules == []
    assert result.rule_score == 0.0

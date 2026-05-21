"""Unit tests for fraud rules."""

import uuid
from datetime import datetime, timezone

from consumer.rules import UserStats, evaluate_rules
from shared.fx import to_usd
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


def _amount_usd(event: TransactionEvent) -> float:
    return to_usd(event.amount, event.currency)


def test_geo_mismatch_triggers():
    event = _event(country="US", ip_country="RU")
    result = evaluate_rules(event, UserStats(), amount_usd=_amount_usd(event))
    assert "GEO_MISMATCH" in result.triggered_rules
    assert result.hard_decline is True


def test_velocity_triggers():
    stats = UserStats(tx_count_1h=6)
    event = _event()
    result = evaluate_rules(event, stats, amount_usd=_amount_usd(event))
    assert "VELOCITY_1H" in result.triggered_rules
    assert result.hard_decline is True


def test_high_amount_triggers():
    stats = UserStats(amount_p99=100.0)
    event = _event(amount=500.0)
    result = evaluate_rules(event, stats, amount_usd=_amount_usd(event))
    assert "HIGH_AMOUNT" in result.triggered_rules


def test_high_amount_uses_usd_not_local():
    """500 USD equivalent in EUR should trigger even if local amount looks small."""
    stats = UserStats(amount_p99=400.0)
    # ~463 EUR ≈ 500 USD at rate 1.08
    event = _event(amount=463.0, currency="EUR")
    result = evaluate_rules(event, stats, amount_usd=500.0)
    assert "HIGH_AMOUNT" in result.triggered_rules


def test_new_merchant_high_triggers():
    stats = UserStats(amount_p95=100.0, seen_merchants={"m_other"})
    event = _event(merchant_id="m_new", amount=200.0)
    result = evaluate_rules(event, stats, amount_usd=_amount_usd(event))
    assert "NEW_MERCHANT_HIGH" in result.triggered_rules


def test_clean_transaction_no_rules():
    stats = UserStats(tx_count_1h=1, amount_p99=1000.0, seen_merchants={"m_001"})
    event = _event(amount=50.0)
    result = evaluate_rules(event, stats, amount_usd=_amount_usd(event))
    assert result.triggered_rules == []
    assert result.rule_score == 0.0

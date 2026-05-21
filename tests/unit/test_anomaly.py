"""Unit tests for anomaly scoring."""

from datetime import datetime, timezone
import uuid

from consumer.anomaly import compute_anomaly_score, z_score_anomaly
from shared.schema import PaymentMethod, TransactionEvent


def _event(amount: float) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=uuid.uuid4(),
        user_id="user_001",
        timestamp=datetime.now(timezone.utc),
        amount=amount,
        merchant_id="m_001",
        merchant_category="5411",
        country="US",
        payment_method=PaymentMethod.CARD,
        ip_country="US",
    )


def test_z_score_normal_amount_low():
    score = z_score_anomaly(50.0, user_mean=50.0, user_std=20.0)
    assert score < 20


def test_z_score_extreme_amount_high():
    score = z_score_anomaly(5000.0, user_mean=50.0, user_std=20.0)
    assert score >= 70


def test_compute_anomaly_without_user_history():
    score = compute_anomaly_score(_event(5000.0))
    assert 0 <= score <= 100

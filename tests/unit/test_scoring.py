"""Unit tests for multi-tier composite scoring."""

from datetime import datetime, timezone
from uuid import uuid4

from consumer.classifier import ClassifierConfig, ClassifierThresholds
from consumer.rules import RuleResult
from consumer.scoring import RiskTier, assign_risk_tier, compute_tier_score
from shared.schema import PaymentMethod, TransactionEvent


def _event(payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=uuid4(),
        user_id="user_1",
        timestamp=datetime(2017, 1, 2, 12, 0, tzinfo=timezone.utc),
        amount=100.0,
        currency="USD",
        merchant_id="m1",
        merchant_category="6012",
        country="US",
        payment_method=payment_method,
        ip_country="US",
    )


def _clf_config(t_low: float = 0.05, t_high: float = 0.20) -> ClassifierConfig:
    return ClassifierConfig(
        model_version="test_xgb",
        feature_columns=[],
        categorical_features=[],
        thresholds=ClassifierThresholds(
            threshold_low=t_low,
            threshold_high=t_high,
            best_threshold=t_high,
        ),
    )


def test_hard_decline_is_block_tier():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=50, triggered_rules=["GEO_MISMATCH"], hard_decline=True),
        anomaly_score=10.0,
        ml_prob=0.99,
        threshold_low=0.05,
        threshold_high=0.20,
        rule_review_threshold=50,
        anomaly_review_threshold=70,
    )
    assert tier == RiskTier.BLOCK
    assert "HARD_DECLINE" in reasons


def test_high_ml_prob_is_strong_suspect():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=10.0,
        ml_prob=0.25,
        threshold_low=0.05,
        threshold_high=0.20,
        rule_review_threshold=50,
        anomaly_review_threshold=70,
    )
    assert tier == RiskTier.STRONG_SUSPECT
    assert "ML_STRONG_SUSPECT" in reasons


def test_low_ml_prob_is_review():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=10.0,
        ml_prob=0.08,
        threshold_low=0.05,
        threshold_high=0.20,
        rule_review_threshold=50,
        anomaly_review_threshold=70,
    )
    assert tier == RiskTier.REVIEW
    assert "ML_REVIEW" in reasons


def test_card_payment_out_of_scope_without_rules():
    event = _event(payment_method=PaymentMethod.CARD)
    score = compute_tier_score(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=5.0,
        ml_prob=None,
        classifier_config=_clf_config(),
    )
    assert score.risk_tier == RiskTier.OUT_OF_SCOPE.value
    assert score.is_fraud is False
    assert score.requires_user_confirmation is False


def test_rule_review_threshold_triggers_confirmation():
    event = _event()
    score = compute_tier_score(
        event,
        RuleResult(rule_score=55, triggered_rules=["HIGH_AMOUNT"], hard_decline=False),
        anomaly_score=5.0,
        ml_prob=0.01,
        classifier_config=_clf_config(),
    )
    assert score.risk_tier == RiskTier.REVIEW.value
    assert score.requires_user_confirmation is True
    assert score.is_fraud is False


def test_strong_suspect_is_fraud_not_confirmation():
    event = _event()
    score = compute_tier_score(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=5.0,
        ml_prob=0.30,
        classifier_config=_clf_config(),
    )
    assert score.risk_tier == RiskTier.STRONG_SUSPECT.value
    assert score.is_fraud is True
    assert score.requires_user_confirmation is False

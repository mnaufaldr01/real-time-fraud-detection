"""Unit tests for multi-tier composite scoring."""

from datetime import datetime, timezone
from uuid import uuid4

from consumer.classifier import ClassifierConfig, ClassifierThresholds
from consumer.rules import RuleResult
from consumer.scoring import RiskTier, TierParams, assign_risk_tier, compute_tier_score
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


def _params(
    t_low: float = 0.05,
    t_high: float = 0.20,
    *,
    rule_soft: float = 50,
    rule_strong: float = 85,
    anomaly_soft: float = 70,
    card_rule_soft: float = 60,
    card_anomaly_soft: float = 80,
) -> TierParams:
    return TierParams(
        threshold_low=t_low,
        threshold_high=t_high,
        rule_soft_threshold=rule_soft,
        rule_strong_suspect_threshold=rule_strong,
        anomaly_soft_threshold=anomaly_soft,
        soft_signals_required=2,
        card_wallet_rule_soft_threshold=card_rule_soft,
        card_wallet_anomaly_soft_threshold=card_anomaly_soft,
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
        params=_params(),
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
        params=_params(),
    )
    assert tier == RiskTier.STRONG_SUSPECT
    assert "ML_STRONG_SUSPECT" in reasons


def test_high_rule_score_is_strong_suspect():
    event = _event()
    rule_result = RuleResult(
        rule_score=90,
        triggered_rules=["HIGH_AMOUNT", "GEO_MISMATCH"],
        hard_decline=False,
    )
    tier, reasons = assign_risk_tier(
        event,
        rule_result,
        anomaly_score=10.0,
        ml_prob=0.01,
        params=_params(),
    )
    assert tier == RiskTier.STRONG_SUSPECT
    assert "RULE_STRONG_SUSPECT" in reasons


def test_single_ml_soft_signal_approves():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=10.0,
        ml_prob=0.08,
        params=_params(),
    )
    assert tier == RiskTier.APPROVE
    assert "ML_SOFT" in reasons
    assert "SOFT_SIGNAL_OBSERVED" in reasons
    assert "MULTI_SIGNAL_REVIEW" not in reasons


def test_two_soft_signals_trigger_review():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=55, triggered_rules=["HIGH_AMOUNT"], hard_decline=False),
        anomaly_score=75.0,
        ml_prob=0.01,
        params=_params(),
    )
    assert tier == RiskTier.REVIEW
    assert "RULE_SOFT" in reasons
    assert "ANOMALY_SOFT" in reasons
    assert "MULTI_SIGNAL_REVIEW" in reasons


def test_ml_and_anomaly_soft_signals_trigger_review():
    event = _event()
    tier, reasons = assign_risk_tier(
        event,
        RuleResult(rule_score=0, triggered_rules=[], hard_decline=False),
        anomaly_score=75.0,
        ml_prob=0.08,
        params=_params(),
    )
    assert tier == RiskTier.REVIEW
    assert "ML_SOFT" in reasons
    assert "ANOMALY_SOFT" in reasons


def test_card_payment_out_of_scope_without_signals():
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
    assert score.is_flagged is False
    assert score.requires_user_confirmation is False


def test_card_single_soft_signal_approves():
    event = _event(payment_method=PaymentMethod.CARD)
    score = compute_tier_score(
        event,
        RuleResult(rule_score=65, triggered_rules=["HIGH_AMOUNT"], hard_decline=False),
        anomaly_score=5.0,
        ml_prob=None,
        classifier_config=_clf_config(),
        tier_params=_params(),
    )
    assert score.risk_tier == RiskTier.APPROVE.value
    assert score.is_flagged is False
    assert "RULE_SOFT" in score.flag_reasons


def test_card_two_soft_signals_trigger_review():
    event = _event(payment_method=PaymentMethod.CARD)
    score = compute_tier_score(
        event,
        RuleResult(rule_score=65, triggered_rules=["HIGH_AMOUNT"], hard_decline=False),
        anomaly_score=85.0,
        ml_prob=None,
        classifier_config=_clf_config(),
        tier_params=_params(),
    )
    assert score.risk_tier == RiskTier.REVIEW.value
    assert score.is_flagged is True
    assert score.requires_user_confirmation is True
    assert score.is_fraud is False


def test_strong_suspect_is_fraud_and_flagged():
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
    assert score.is_flagged is True
    assert score.requires_user_confirmation is False


def test_review_is_flagged_not_fraud():
    event = _event()
    score = compute_tier_score(
        event,
        RuleResult(rule_score=55, triggered_rules=["HIGH_AMOUNT"], hard_decline=False),
        anomaly_score=75.0,
        ml_prob=0.01,
        classifier_config=_clf_config(),
        tier_params=_params(),
    )
    assert score.risk_tier == RiskTier.REVIEW.value
    assert score.is_flagged is True
    assert score.is_fraud is False
    assert score.requires_user_confirmation is True

"""Unit tests for composite scoring."""

from consumer.rules import RuleResult
from consumer.scoring import compute_final_score


def test_hard_decline_overrides_low_score():
    rule_result = RuleResult(rule_score=50, triggered_rules=["GEO_MISMATCH"], hard_decline=True)
    score = compute_final_score(rule_result, anomaly_score=10.0)
    assert score.is_fraud is True
    assert "HARD_DECLINE" in score.flag_reasons or "GEO_MISMATCH" in score.flag_reasons


def test_threshold_flags_fraud():
    rule_result = RuleResult(rule_score=80, triggered_rules=["HIGH_AMOUNT"], hard_decline=False)
    score = compute_final_score(rule_result, anomaly_score=70.0)
    assert score.is_fraud is True
    assert score.final_score >= 70


def test_clean_score_not_fraud():
    rule_result = RuleResult(rule_score=0, triggered_rules=[], hard_decline=False)
    score = compute_final_score(rule_result, anomaly_score=5.0)
    assert score.is_fraud is False
    assert score.final_score < 70

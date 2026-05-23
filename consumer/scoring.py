"""Multi-tier composite scoring: rules + XGBoost + anomaly."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from consumer.classifier import ClassifierConfig, get_classifier_config, is_ml_scoring_scope
from consumer.config import config
from consumer.rules import RuleResult
from shared.schema import TransactionEvent


class RiskTier(str, Enum):
    """Production risk tiers (0–4)."""

    OUT_OF_SCOPE = "out_of_scope"  # tier 0 — non bank_transfer; rules only
    BLOCK = "block"  # tier 1 — hard-decline rules
    STRONG_SUSPECT = "strong_suspect"  # tier 2 — high ML confidence
    REVIEW = "review"  # tier 3 — soft suspect / user confirmation
    APPROVE = "approve"  # tier 4 — clean


@dataclass
class ScoreResult:
    rule_score: float
    anomaly_score: float
    final_score: float
    ml_prob: Optional[float]
    risk_tier: str
    requires_user_confirmation: bool
    is_fraud: bool
    flag_reasons: list[str]
    ruleset_version: str
    model_version: str


def _composite_score(
    rule_score: float,
    anomaly_score: float,
    ml_prob: Optional[float],
) -> float:
    ml_component = (ml_prob or 0.0) * 100.0
    return round(min(max(rule_score, anomaly_score, ml_component), 100.0), 2)


def assign_risk_tier(
    event: TransactionEvent,
    rule_result: RuleResult,
    anomaly_score: float,
    ml_prob: Optional[float],
    *,
    threshold_low: float,
    threshold_high: float,
    rule_review_threshold: float,
    anomaly_review_threshold: float,
) -> tuple[RiskTier, list[str]]:
    """Cascade tier assignment (rules → ML → review → approve)."""
    reasons = list(rule_result.triggered_rules)
    in_ml_scope = is_ml_scoring_scope(event)

    if rule_result.hard_decline:
        if "HARD_DECLINE" not in reasons:
            reasons.append("HARD_DECLINE")
        return RiskTier.BLOCK, reasons

    if in_ml_scope and ml_prob is not None:
        if ml_prob >= threshold_high:
            reasons.append("ML_STRONG_SUSPECT")
            return RiskTier.STRONG_SUSPECT, reasons
        if ml_prob >= threshold_low:
            reasons.append("ML_REVIEW")
            return RiskTier.REVIEW, reasons

    if rule_result.rule_score >= rule_review_threshold:
        reasons.append("RULE_REVIEW")
        return RiskTier.REVIEW, reasons

    if anomaly_score >= anomaly_review_threshold:
        reasons.append("HIGH_ANOMALY")
        return RiskTier.REVIEW, reasons

    if not in_ml_scope:
        reasons.append("OUT_OF_SCOPE")
        return RiskTier.OUT_OF_SCOPE, reasons

    return RiskTier.APPROVE, reasons


def compute_tier_score(
    event: TransactionEvent,
    rule_result: RuleResult,
    anomaly_score: float,
    ml_prob: Optional[float] = None,
    *,
    ruleset_version: str | None = None,
    model_version: str | None = None,
    classifier_config: ClassifierConfig | None = None,
) -> ScoreResult:
    """Score a transaction into tiers 0–4."""
    ruleset_version = ruleset_version or config.ruleset_version
    clf = classifier_config or get_classifier_config()

    if clf is not None:
        model_version = model_version or clf.model_version
        t_low = clf.thresholds.threshold_low
        t_high = clf.thresholds.threshold_high
    else:
        model_version = model_version or config.model_version
        t_low = config.ml_threshold_low
        t_high = config.ml_threshold_high

    tier, flag_reasons = assign_risk_tier(
        event,
        rule_result,
        anomaly_score,
        ml_prob,
        threshold_low=t_low,
        threshold_high=t_high,
        rule_review_threshold=config.rule_review_threshold,
        anomaly_review_threshold=config.anomaly_review_threshold,
    )

    is_fraud = tier in (RiskTier.BLOCK, RiskTier.STRONG_SUSPECT)
    requires_user_confirmation = tier == RiskTier.REVIEW
    final_score = _composite_score(rule_result.rule_score, anomaly_score, ml_prob)

    return ScoreResult(
        rule_score=round(rule_result.rule_score, 2),
        anomaly_score=round(anomaly_score, 2),
        final_score=final_score,
        ml_prob=round(ml_prob, 6) if ml_prob is not None else None,
        risk_tier=tier.value,
        requires_user_confirmation=requires_user_confirmation,
        is_fraud=is_fraud,
        flag_reasons=flag_reasons,
        ruleset_version=ruleset_version,
        model_version=model_version,
    )


def compute_final_score(
    rule_result: RuleResult,
    anomaly_score: float,
    *,
    event: TransactionEvent | None = None,
    ml_prob: Optional[float] = None,
    ruleset_version: str | None = None,
    model_version: str | None = None,
) -> ScoreResult:
    """Backward-compatible entry point; requires ``event`` for tier scoring."""
    if event is None:
        raise ValueError("compute_final_score requires event= for multi-tier scoring")
    return compute_tier_score(
        event,
        rule_result,
        anomaly_score,
        ml_prob=ml_prob,
        ruleset_version=ruleset_version,
        model_version=model_version,
    )

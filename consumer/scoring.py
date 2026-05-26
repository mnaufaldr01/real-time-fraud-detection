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
    STRONG_SUSPECT = "strong_suspect"  # tier 2 — high ML confidence or rule score
    REVIEW = "review"  # tier 3 — multi-signal soft suspect / user confirmation
    APPROVE = "approve"  # tier 4 — clean


@dataclass(frozen=True)
class TierParams:
    """Thresholds for multi-signal tier assignment."""

    threshold_low: float
    threshold_high: float
    rule_soft_threshold: float
    rule_strong_suspect_threshold: float
    anomaly_soft_threshold: float
    soft_signals_required: int
    card_wallet_rule_soft_threshold: float
    card_wallet_anomaly_soft_threshold: float


@dataclass
class ScoreResult:
    rule_score: float
    anomaly_score: float
    final_score: float
    ml_prob: Optional[float]
    risk_tier: str
    requires_user_confirmation: bool
    is_fraud: bool
    is_flagged: bool
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


def _soft_thresholds(event: TransactionEvent, params: TierParams) -> tuple[float, float]:
    """Payment-method-aware soft thresholds (card/wallet are stricter)."""
    if is_ml_scoring_scope(event):
        return params.rule_soft_threshold, params.anomaly_soft_threshold
    return params.card_wallet_rule_soft_threshold, params.card_wallet_anomaly_soft_threshold


def _count_soft_signals(
    event: TransactionEvent,
    rule_result: RuleResult,
    anomaly_score: float,
    ml_prob: Optional[float],
    params: TierParams,
) -> tuple[int, list[str]]:
    """Count independent soft signals for multi-signal review."""
    in_ml_scope = is_ml_scoring_scope(event)
    rule_soft, anomaly_soft = _soft_thresholds(event, params)
    soft_reasons: list[str] = []
    count = 0

    if (
        in_ml_scope
        and ml_prob is not None
        and params.threshold_low <= ml_prob < params.threshold_high
    ):
        count += 1
        soft_reasons.append("ML_SOFT")

    if rule_soft <= rule_result.rule_score < params.rule_strong_suspect_threshold:
        count += 1
        soft_reasons.append("RULE_SOFT")

    if anomaly_score >= anomaly_soft:
        count += 1
        soft_reasons.append("ANOMALY_SOFT")

    return count, soft_reasons


def assign_risk_tier(
    event: TransactionEvent,
    rule_result: RuleResult,
    anomaly_score: float,
    ml_prob: Optional[float],
    *,
    params: TierParams,
) -> tuple[RiskTier, list[str]]:
    """Multi-signal tier assignment: evaluate all signals, then pick highest tier."""
    reasons = list(rule_result.triggered_rules)
    in_ml_scope = is_ml_scoring_scope(event)

    if rule_result.hard_decline:
        if "HARD_DECLINE" not in reasons:
            reasons.append("HARD_DECLINE")
        return RiskTier.BLOCK, reasons

    strong_reasons: list[str] = []
    if in_ml_scope and ml_prob is not None and ml_prob >= params.threshold_high:
        strong_reasons.append("ML_STRONG_SUSPECT")
    if rule_result.rule_score >= params.rule_strong_suspect_threshold:
        strong_reasons.append("RULE_STRONG_SUSPECT")

    if strong_reasons:
        reasons.extend(strong_reasons)
        return RiskTier.STRONG_SUSPECT, reasons

    soft_count, soft_reasons = _count_soft_signals(
        event, rule_result, anomaly_score, ml_prob, params
    )

    if soft_count >= params.soft_signals_required:
        reasons.extend(soft_reasons)
        reasons.append("MULTI_SIGNAL_REVIEW")
        return RiskTier.REVIEW, reasons

    if soft_count == 1:
        reasons.extend(soft_reasons)
        reasons.append("SOFT_SIGNAL_OBSERVED")

    if not in_ml_scope and soft_count == 0:
        reasons.append("OUT_OF_SCOPE")
        return RiskTier.OUT_OF_SCOPE, reasons

    return RiskTier.APPROVE, reasons


def _tier_params_from_config(
    clf: ClassifierConfig | None,
) -> TierParams:
    if clf is not None:
        t_low = clf.thresholds.threshold_low
        t_high = clf.thresholds.threshold_high
    else:
        t_low = config.ml_threshold_low
        t_high = config.ml_threshold_high

    return TierParams(
        threshold_low=t_low,
        threshold_high=t_high,
        rule_soft_threshold=config.rule_soft_threshold,
        rule_strong_suspect_threshold=config.rule_strong_suspect_threshold,
        anomaly_soft_threshold=config.anomaly_soft_threshold,
        soft_signals_required=config.soft_signals_required,
        card_wallet_rule_soft_threshold=config.card_wallet_rule_soft_threshold,
        card_wallet_anomaly_soft_threshold=config.card_wallet_anomaly_soft_threshold,
    )


def compute_tier_score(
    event: TransactionEvent,
    rule_result: RuleResult,
    anomaly_score: float,
    ml_prob: Optional[float] = None,
    *,
    ruleset_version: str | None = None,
    model_version: str | None = None,
    classifier_config: ClassifierConfig | None = None,
    tier_params: TierParams | None = None,
) -> ScoreResult:
    """Score a transaction into tiers 0–4."""
    ruleset_version = ruleset_version or config.ruleset_version
    clf = classifier_config or get_classifier_config()
    params = tier_params or _tier_params_from_config(clf)

    if clf is not None:
        model_version = model_version or clf.model_version
    else:
        model_version = model_version or config.model_version

    tier, flag_reasons = assign_risk_tier(
        event,
        rule_result,
        anomaly_score,
        ml_prob,
        params=params,
    )

    is_fraud = tier in (RiskTier.BLOCK, RiskTier.STRONG_SUSPECT)
    requires_user_confirmation = tier == RiskTier.REVIEW
    is_flagged = tier not in (RiskTier.APPROVE, RiskTier.OUT_OF_SCOPE)
    final_score = _composite_score(rule_result.rule_score, anomaly_score, ml_prob)

    return ScoreResult(
        rule_score=round(rule_result.rule_score, 2),
        anomaly_score=round(anomaly_score, 2),
        final_score=final_score,
        ml_prob=round(ml_prob, 6) if ml_prob is not None else None,
        risk_tier=tier.value,
        requires_user_confirmation=requires_user_confirmation,
        is_fraud=is_fraud,
        is_flagged=is_flagged,
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

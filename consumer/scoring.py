"""Composite scoring: rules + anomaly with hard-decline override."""

from dataclasses import dataclass

from consumer.config import config
from consumer.rules import RuleResult


@dataclass
class ScoreResult:
    rule_score: float
    anomaly_score: float
    final_score: float
    is_fraud: bool
    flag_reasons: list[str]
    ruleset_version: str
    model_version: str


def compute_final_score(
    rule_result: RuleResult,
    anomaly_score: float,
    ruleset_version: str | None = None,
    model_version: str | None = None,
) -> ScoreResult:
    """Weighted composite with hard-decline override."""
    ruleset_version = ruleset_version or config.ruleset_version
    model_version = model_version or config.model_version

    final = (
        config.rule_weight * rule_result.rule_score
        + config.anomaly_weight * anomaly_score
    )
    final = round(min(final, 100.0), 2)

    flag_reasons = list(rule_result.triggered_rules)
    if anomaly_score >= 70:
        flag_reasons.append("HIGH_ANOMALY")

    is_fraud = rule_result.hard_decline or final >= config.fraud_threshold

    if is_fraud and final < config.fraud_threshold and rule_result.hard_decline:
        flag_reasons.append("HARD_DECLINE")

    return ScoreResult(
        rule_score=round(rule_result.rule_score, 2),
        anomaly_score=round(anomaly_score, 2),
        final_score=final,
        is_fraud=is_fraud,
        flag_reasons=flag_reasons,
        ruleset_version=ruleset_version,
        model_version=model_version,
    )

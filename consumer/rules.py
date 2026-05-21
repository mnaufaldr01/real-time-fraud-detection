"""Fraud detection rules engine."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from consumer.config import config
from shared.schema import TransactionEvent


@dataclass
class UserStats:
    tx_count_1h: int = 0
    amount_p99: Optional[float] = None
    amount_p95: Optional[float] = None
    seen_merchants: set[str] = field(default_factory=set)


@dataclass
class RuleResult:
    rule_score: float
    triggered_rules: list[str]
    hard_decline: bool


RULE_WEIGHTS = {
    "HIGH_AMOUNT": 40,
    "VELOCITY_1H": 35,
    "GEO_MISMATCH": 50,
    "NEW_MERCHANT_HIGH": 30,
}


def evaluate_rules(
    event: TransactionEvent,
    stats: UserStats,
    *,
    amount_usd: float,
) -> RuleResult:
    """Evaluate all rules and return composite rule score (0-100)."""
    triggered: list[str] = []
    score = 0.0

    amount_p99 = stats.amount_p99 or config.global_amount_p99
    amount_p95 = stats.amount_p95 or config.global_amount_p95

    if amount_usd > amount_p99:
        triggered.append("HIGH_AMOUNT")
        score += RULE_WEIGHTS["HIGH_AMOUNT"]

    if stats.tx_count_1h > config.velocity_1h_limit:
        triggered.append("VELOCITY_1H")
        score += RULE_WEIGHTS["VELOCITY_1H"]

    if event.country != event.ip_country:
        triggered.append("GEO_MISMATCH")
        score += RULE_WEIGHTS["GEO_MISMATCH"]

    if event.merchant_id not in stats.seen_merchants and amount_usd > amount_p95:
        triggered.append("NEW_MERCHANT_HIGH")
        score += RULE_WEIGHTS["NEW_MERCHANT_HIGH"]

    rule_score = min(score, 100.0)
    hard_decline = any(r in config.hard_decline_rules for r in triggered)

    return RuleResult(
        rule_score=rule_score,
        triggered_rules=triggered,
        hard_decline=hard_decline,
    )


def evaluate_rules_batch(
    event: TransactionEvent,
    stats: UserStats,
    *,
    amount_usd: float,
) -> RuleResult:
    """Stricter batch ruleset (batch_v2): lower velocity threshold."""
    triggered: list[str] = []
    score = 0.0

    amount_p99 = stats.amount_p99 or config.global_amount_p99 * 0.85
    amount_p95 = stats.amount_p95 or config.global_amount_p95 * 0.85

    if amount_usd > amount_p99:
        triggered.append("HIGH_AMOUNT")
        score += RULE_WEIGHTS["HIGH_AMOUNT"]

    # Stricter: 3 tx/hour instead of 5
    if stats.tx_count_1h > 3:
        triggered.append("VELOCITY_1H")
        score += RULE_WEIGHTS["VELOCITY_1H"]

    if event.country != event.ip_country:
        triggered.append("GEO_MISMATCH")
        score += RULE_WEIGHTS["GEO_MISMATCH"]

    if event.merchant_id not in stats.seen_merchants and amount_usd > amount_p95:
        triggered.append("NEW_MERCHANT_HIGH")
        score += RULE_WEIGHTS["NEW_MERCHANT_HIGH"]

    rule_score = min(score, 100.0)
    hard_decline = any(r in config.hard_decline_rules for r in triggered)

    return RuleResult(
        rule_score=rule_score,
        triggered_rules=triggered,
        hard_decline=hard_decline,
    )


def rolling_1h_window(now: datetime) -> datetime:
    return now - timedelta(hours=1)

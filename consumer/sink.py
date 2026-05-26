"""PostgreSQL persistence and Kafka scored-topic publisher."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from confluent_kafka import Producer
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from consumer.config import config
from consumer.rules import UserStats, rolling_1h_window
from consumer.scoring import ScoreResult
from shared.schema import TransactionEvent

logger = logging.getLogger(__name__)


class FraudSink:
    def __init__(self, database_url: str | None = None):
        url = database_url or config.database_url
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        self.producer = Producer({"bootstrap.servers": config.kafka_bootstrap})

    def load_user_stats(self, user_id: str, merchant_id: str, now: datetime) -> UserStats:
        """Load rolling user statistics from Postgres."""
        window_start = rolling_1h_window(now)
        stats = UserStats()

        with self.engine.connect() as conn:
            count_row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM transactions
                    WHERE user_id = :user_id
                      AND timestamp >= :window_start
                      AND timestamp < :now
                    """
                ),
                {"user_id": user_id, "window_start": window_start, "now": now},
            ).scalar()
            stats.tx_count_1h = count_row or 0

            percentiles = conn.execute(
                text(
                    """
                    SELECT
                        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount_usd) AS p99,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY amount_usd) AS p95
                    FROM transactions
                    WHERE user_id = :user_id
                      AND timestamp >= :lookback
                    """
                ),
                {
                    "user_id": user_id,
                    "lookback": now.replace(tzinfo=timezone.utc) - timedelta(days=30),
                },
            ).fetchone()

            if percentiles and percentiles[0] is not None:
                stats.amount_p99 = float(percentiles[0])
                stats.amount_p95 = float(percentiles[1])

            merchants = conn.execute(
                text(
                    """
                    SELECT DISTINCT merchant_id FROM transactions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).fetchall()
            stats.seen_merchants = {row[0] for row in merchants}

        return stats

    def load_user_amount_stats(self, user_id: str) -> tuple[Optional[float], Optional[float]]:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT AVG(amount_usd), STDDEV(amount_usd)
                    FROM transactions
                    WHERE user_id = :user_id
                      AND timestamp >= NOW() - INTERVAL '30 days'
                    """
                ),
                {"user_id": user_id},
            ).fetchone()
            if row and row[0] is not None:
                return float(row[0]), float(row[1] or 0)
        return None, None

    def persist(
        self,
        event: TransactionEvent,
        score: ScoreResult,
        *,
        amount_usd: float,
        fx_snapshot_id: int | None = None,
        fx_as_of: datetime | None = None,
    ) -> None:
        """Idempotent upsert of transaction, risk score, and fraud flag."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        transaction_id, user_id, timestamp, amount, currency, amount_usd,
                        merchant_id, merchant_category, country, payment_method,
                        device_id, ip_country, fx_snapshot_id, fx_as_of
                    ) VALUES (
                        :transaction_id, :user_id, :timestamp, :amount, :currency, :amount_usd,
                        :merchant_id, :merchant_category, :country, :payment_method,
                        :device_id, :ip_country, :fx_snapshot_id, :fx_as_of
                    )
                    ON CONFLICT (transaction_id) DO NOTHING
                    """
                ),
                {
                    "transaction_id": str(event.transaction_id),
                    "user_id": event.user_id,
                    "timestamp": event.timestamp,
                    "amount": event.amount,
                    "currency": event.currency,
                    "amount_usd": amount_usd,
                    "merchant_id": event.merchant_id,
                    "merchant_category": event.merchant_category,
                    "country": event.country,
                    "payment_method": event.payment_method.value,
                    "device_id": event.device_id,
                    "ip_country": event.ip_country,
                    "fx_snapshot_id": fx_snapshot_id,
                    "fx_as_of": fx_as_of,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO risk_scores (
                        transaction_id, rule_score, anomaly_score, final_score,
                        ml_prob, ruleset_version, model_version, scored_at
                    ) VALUES (
                        :transaction_id, :rule_score, :anomaly_score, :final_score,
                        :ml_prob, :ruleset_version, :model_version, NOW()
                    )
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        rule_score = EXCLUDED.rule_score,
                        anomaly_score = EXCLUDED.anomaly_score,
                        final_score = EXCLUDED.final_score,
                        ml_prob = EXCLUDED.ml_prob,
                        ruleset_version = EXCLUDED.ruleset_version,
                        model_version = EXCLUDED.model_version,
                        scored_at = EXCLUDED.scored_at
                    """
                ),
                {
                    "transaction_id": str(event.transaction_id),
                    "rule_score": score.rule_score,
                    "anomaly_score": score.anomaly_score,
                    "final_score": score.final_score,
                    "ml_prob": score.ml_prob,
                    "ruleset_version": score.ruleset_version,
                    "model_version": score.model_version,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO fraud_flags (
                        transaction_id, is_fraud, is_flagged, flag_reasons,
                        risk_tier, requires_user_confirmation, ml_prob,
                        ruleset_version, scored_at
                    ) VALUES (
                        :transaction_id, :is_fraud, :is_flagged, CAST(:flag_reasons AS jsonb),
                        :risk_tier, :requires_user_confirmation, :ml_prob,
                        :ruleset_version, NOW()
                    )
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        is_fraud = EXCLUDED.is_fraud,
                        is_flagged = EXCLUDED.is_flagged,
                        flag_reasons = EXCLUDED.flag_reasons,
                        risk_tier = EXCLUDED.risk_tier,
                        requires_user_confirmation = EXCLUDED.requires_user_confirmation,
                        ml_prob = EXCLUDED.ml_prob,
                        ruleset_version = EXCLUDED.ruleset_version,
                        scored_at = EXCLUDED.scored_at
                    """
                ),
                {
                    "transaction_id": str(event.transaction_id),
                    "is_fraud": score.is_fraud,
                    "is_flagged": score.is_flagged,
                    "flag_reasons": json.dumps(score.flag_reasons),
                    "risk_tier": score.risk_tier,
                    "requires_user_confirmation": score.requires_user_confirmation,
                    "ml_prob": score.ml_prob,
                    "ruleset_version": score.ruleset_version,
                },
            )

        self._publish_scored(event, score)

    def _publish_scored(self, event: TransactionEvent, score: ScoreResult) -> None:
        payload = {
            "transaction_id": str(event.transaction_id),
            "user_id": event.user_id,
            "final_score": score.final_score,
            "ml_prob": score.ml_prob,
            "risk_tier": score.risk_tier,
            "requires_user_confirmation": score.requires_user_confirmation,
            "is_fraud": score.is_fraud,
            "is_flagged": score.is_flagged,
            "flag_reasons": score.flag_reasons,
            "ruleset_version": score.ruleset_version,
        }
        self.producer.produce(
            config.topic_scored,
            key=event.user_id.encode("utf-8"),
            value=json.dumps(payload).encode("utf-8"),
        )
        self.producer.poll(0)

    def flush(self) -> None:
        self.producer.flush()

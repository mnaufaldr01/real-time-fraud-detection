"""Daily batch re-scoring DAG with stricter ruleset (batch_v2)."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

from airflow import DAG

# Allow importing consumer modules inside Airflow container
sys.path.insert(0, "/opt/airflow")

from consumer.anomaly import compute_anomaly_score
from consumer.config import config
from consumer.rules import UserStats, evaluate_rules_batch
from consumer.scoring import compute_final_score

logger = logging.getLogger(__name__)

FRAUD_DB_URL = os.getenv(
    "FRAUD_DATABASE_URL",
    "postgresql+psycopg2://fraud:fraud@postgres:5432/fraud_db",
)


def _get_engine():
    return create_engine(FRAUD_DB_URL, pool_pre_ping=True)


def extract_and_rescore(**context):
    dag_run_id = context["dag_run"].run_id
    started_at = datetime.now(timezone.utc)
    engine = _get_engine()
    rows_processed = 0

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO batch_runs (dag_run_id, started_at, rows_processed,
                    ruleset_version, pipeline_version, status)
                VALUES (:dag_run_id, :started_at, 0, :ruleset, :pipeline, 'running')
                """
            ),
            {
                "dag_run_id": dag_run_id,
                "started_at": started_at,
                "ruleset": config.batch_ruleset_version,
                "pipeline": config.batch_pipeline_version,
            },
        )

    try:
        lookback = datetime.now(timezone.utc) - timedelta(days=7)

        with _get_engine().connect() as conn:
            transactions = conn.execute(
                text(
                    """
                    SELECT transaction_id, user_id, timestamp, amount, currency, amount_usd,
                           merchant_id, merchant_category, country, payment_method,
                           device_id, ip_country
                    FROM transactions
                    WHERE timestamp >= :lookback
                    ORDER BY timestamp
                    """
                ),
                {"lookback": lookback},
            ).fetchall()

        from shared.fx import to_usd
        from shared.fx_provider import DbFxSnapshotProvider
        from shared.schema import PaymentMethod, TransactionEvent

        fx_provider = DbFxSnapshotProvider(engine)
        fx_snapshot = fx_provider.get_snapshot()

        for row in transactions:
            event = TransactionEvent(
                transaction_id=row[0],
                user_id=row[1],
                timestamp=row[2],
                amount=float(row[3]),
                currency=row[4],
                merchant_id=row[6],
                merchant_category=row[7],
                country=row[8],
                payment_method=PaymentMethod(row[9]),
                device_id=row[10],
                ip_country=row[11],
            )
            if row[5] is not None:
                amount_usd = float(row[5])
            else:
                amount_usd = to_usd(
                    event.amount, event.currency, rates=fx_snapshot.rates
                )

            stats = _load_stats(engine, event.user_id, event.merchant_id, event.timestamp)
            user_mean, user_std = _load_amount_stats(engine, event.user_id)

            rule_result = evaluate_rules_batch(event, stats, amount_usd=amount_usd)
            anomaly_score = compute_anomaly_score(
                event, user_mean, user_std, amount_usd=amount_usd
            )
            score = compute_final_score(
                rule_result,
                anomaly_score,
                ruleset_version=config.batch_ruleset_version,
                model_version=config.model_version,
            )

            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO risk_scores_history (
                            transaction_id, rule_score, anomaly_score, final_score,
                            ruleset_version, model_version, pipeline_version, scored_at
                        ) VALUES (
                            :transaction_id, :rule_score, :anomaly_score, :final_score,
                            :ruleset_version, :model_version, :pipeline_version, NOW()
                        )
                        """
                    ),
                    {
                        "transaction_id": str(event.transaction_id),
                        "rule_score": score.rule_score,
                        "anomaly_score": score.anomaly_score,
                        "final_score": score.final_score,
                        "ruleset_version": score.ruleset_version,
                        "model_version": score.model_version,
                        "pipeline_version": config.batch_pipeline_version,
                    },
                )
            rows_processed += 1

        mismatch_pct = _compute_mismatch_pct(engine)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE batch_runs
                    SET finished_at = :finished_at, rows_processed = :rows_processed,
                        status = 'success'
                    WHERE dag_run_id = :dag_run_id
                    """
                ),
                {
                    "finished_at": datetime.now(timezone.utc),
                    "rows_processed": rows_processed,
                    "dag_run_id": dag_run_id,
                },
            )

        logger.info(
            "Batch rescore complete: rows=%d, stream_vs_batch_mismatch=%.1f%%",
            rows_processed,
            mismatch_pct,
        )
        return {"rows_processed": rows_processed, "mismatch_pct": mismatch_pct}

    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE batch_runs
                    SET finished_at = :finished_at, status = 'failed', error_message = :error
                    WHERE dag_run_id = :dag_run_id
                    """
                ),
                {
                    "finished_at": datetime.now(timezone.utc),
                    "error": str(exc),
                    "dag_run_id": dag_run_id,
                },
            )
        raise


def _load_stats(engine, user_id: str, merchant_id: str, now: datetime) -> UserStats:
    from consumer.rules import rolling_1h_window

    stats = UserStats()
    window_start = rolling_1h_window(now)

    with engine.connect() as conn:
        stats.tx_count_1h = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM transactions
                WHERE user_id = :user_id AND timestamp >= :ws AND timestamp < :now
                """
            ),
            {"user_id": user_id, "ws": window_start, "now": now},
        ).scalar() or 0

        row = conn.execute(
            text(
                """
                SELECT
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount_usd),
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY amount_usd)
                FROM transactions
                WHERE user_id = :user_id AND timestamp >= NOW() - INTERVAL '30 days'
                """
            ),
            {"user_id": user_id},
        ).fetchone()

        if row and row[0]:
            stats.amount_p99 = float(row[0])
            stats.amount_p95 = float(row[1])

        merchants = conn.execute(
            text("SELECT DISTINCT merchant_id FROM transactions WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).fetchall()
        stats.seen_merchants = {m[0] for m in merchants}

    return stats


def _load_amount_stats(engine, user_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT AVG(amount_usd), STDDEV(amount_usd) FROM transactions
                WHERE user_id = :user_id AND timestamp >= NOW() - INTERVAL '30 days'
                """
            ),
            {"user_id": user_id},
        ).fetchone()
        if row and row[0]:
            return float(row[0]), float(row[1] or 0)
    return None, None


def _compute_mismatch_pct(engine) -> float:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE ABS(rs.final_score - rsh.final_score) > 5
                           OR rs.final_score IS NULL
                    ) AS mismatched
                FROM risk_scores_history rsh
                LEFT JOIN risk_scores rs ON rs.transaction_id = rsh.transaction_id
                WHERE rsh.scored_at >= NOW() - INTERVAL '1 day'
                """
            )
        ).fetchone()
        if not row or row[0] == 0:
            return 0.0
        return round(row[1] / row[0] * 100, 1)


def run_data_quality_checks(**context):
    engine = _get_engine()
    with engine.connect() as conn:
        invalid_scores = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM risk_scores
                WHERE final_score NOT BETWEEN 0 AND 100
                """
            )
        ).scalar()

        fraud_rate = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE is_fraud) * 100.0 / NULLIF(COUNT(*), 0)
                FROM fraud_flags
                WHERE scored_at >= NOW() - INTERVAL '24 hours'
                """
            )
        ).scalar()

    if invalid_scores and invalid_scores > 0:
        raise ValueError(f"Found {invalid_scores} scores outside 0-100 range")

    if fraud_rate and fraud_rate > 20:
        raise ValueError(f"Fraud rate {fraud_rate:.1f}% exceeds 20% threshold")

    logger.info("Data quality checks passed (fraud_rate_24h=%.2f%%)", fraud_rate or 0)
    return {"fraud_rate_24h": fraud_rate}


default_args = {
    "owner": "fraud-team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="daily_rescore",
    default_args=default_args,
    description="Batch re-score last 7 days with stricter ruleset (batch_v2)",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["fraud", "batch"],
) as dag:
    rescore_task = PythonOperator(
        task_id="extract_and_rescore",
        python_callable=extract_and_rescore,
    )

    quality_task = PythonOperator(
        task_id="data_quality_checks",
        python_callable=run_data_quality_checks,
    )

    rescore_task >> quality_task

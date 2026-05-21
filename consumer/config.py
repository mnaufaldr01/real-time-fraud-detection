"""Consumer configuration with env overrides."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "anomaly_v1.joblib"


@dataclass(frozen=True)
class Config:
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic_raw: str = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
    topic_scored: str = os.getenv("KAFKA_TOPIC_SCORED", "transactions.scored")
    topic_dlq: str = os.getenv("KAFKA_TOPIC_DLQ", "transactions.dlq")
    consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "fraud-scorer-v1")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://fraud:fraud@localhost:5432/fraud_db"
    )
    fraud_threshold: float = float(os.getenv("FRAUD_SCORE_THRESHOLD", "70"))
    ruleset_version: str = os.getenv("RULESET_VERSION", "stream_v1")
    model_version: str = os.getenv("MODEL_VERSION", "anomaly_v1")
    batch_ruleset_version: str = os.getenv("BATCH_RULESET_VERSION", "batch_v2")
    batch_pipeline_version: str = os.getenv("BATCH_PIPELINE_VERSION", "batch_v2")

    # Rule thresholds derived from profiling
    high_amount_percentile: float = float(os.getenv("HIGH_AMOUNT_PERCENTILE", "99"))
    velocity_1h_limit: int = int(os.getenv("VELOCITY_1H_LIMIT", "5"))
    new_merchant_amount_percentile: float = float(
        os.getenv("NEW_MERCHANT_AMOUNT_PERCENTILE", "95")
    )

    # Global defaults when no user history (from profiling)
    global_amount_p95: float = float(os.getenv("GLOBAL_AMOUNT_P95", "450.0"))
    global_amount_p99: float = float(os.getenv("GLOBAL_AMOUNT_P99", "850.0"))

    # Scoring weights
    rule_weight: float = 0.6
    anomaly_weight: float = 0.4

    # Hard-decline rules
    hard_decline_rules: tuple = ("GEO_MISMATCH", "VELOCITY_1H")


config = Config()

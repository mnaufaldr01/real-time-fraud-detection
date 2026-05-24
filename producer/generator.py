"""Synthetic transaction generator with fraud pattern injection."""

import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

from confluent_kafka import Producer
from dotenv import load_dotenv
from faker import Faker

from shared.fx import assign_currency, country_for_currency
from shared.synthetic import build_transaction, pick_fraud_destination

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
RATE_MIN = float(os.getenv("GENERATOR_RATE_MIN", "1"))
RATE_MAX = float(os.getenv("GENERATOR_RATE_MAX", "5"))
FRAUD_RATE = float(os.getenv("FRAUD_INJECTION_RATE", "0.03"))

GENERATOR_LIVE = os.getenv("GENERATOR_LIVE", "false").lower() in ("1", "true", "yes")
SIM_START = datetime.fromisoformat(
    os.getenv("GENERATOR_SIM_START", "2025-01-01T00:00:00+00:00")
)
SIM_END = datetime.fromisoformat(
    os.getenv("GENERATOR_SIM_END", "2026-04-30T23:59:59+00:00")
)
SIM_TOTAL = int(os.getenv("GENERATOR_SIM_TOTAL", "30000"))
SIM_SLEEP_SEC = float(os.getenv("GENERATOR_SIM_SLEEP", "0"))

_user_pool: list[str] = [f"user_{i:05d}" for i in range(500)]


def _next_timestamp() -> datetime:
    """Live mode: now. Simulation mode: uniform random instant in [SIM_START, SIM_END]."""
    if GENERATOR_LIVE:
        return datetime.now(timezone.utc)
    span_seconds = (SIM_END - SIM_START).total_seconds()
    offset = random.uniform(0, span_seconds)
    return SIM_START + timedelta(seconds=offset)


def _normal_transaction(
    user_id: str | None = None,
    timestamp: datetime | None = None,
    merchant_id: str | None = None,
    merchant_category: str | None = None,
) -> dict:
    uid = user_id or random.choice(_user_pool)
    reference = round(random.lognormvariate(3.5, 0.8), 2)
    return build_transaction(
        user_id=uid,
        reference_amount=reference,
        timestamp=timestamp or _next_timestamp(),
        merchant_id=merchant_id,
        merchant_category=merchant_category,
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def _fraud_destination() -> tuple[str, str]:
    """Most fraud targets a small set of payout merchants; ~15% stay random."""
    if random.random() < 0.85:
        return pick_fraud_destination()
    return f"m_{fake.uuid4()[:8]}", random.choice(
        ("7995", "6011", "5999", "5541")
    )


def _fraud_transaction(timestamp: datetime | None = None) -> dict:
    """Inject one of several fraud patterns (reference amounts in USD scale)."""
    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    user_id = random.choice(_user_pool)
    ts = timestamp or _next_timestamp()
    merchant_id, merchant_category = _fraud_destination()

    if pattern == "velocity":
        return build_transaction(
            user_id=user_id,
            reference_amount=round(random.uniform(20, 100), 2),
            timestamp=ts,
            merchant_id=merchant_id,
            merchant_category=merchant_category,
            device_id=f"dev_{fake.uuid4()[:8]}",
        )

    if pattern == "geo_mismatch":
        currency = assign_currency(user_id)
        country = country_for_currency(currency, user_id)
        mismatched = [c for c in ("US", "GB", "DE", "FR", "AU", "SG", "ID") if c != country]
        return build_transaction(
            user_id=user_id,
            reference_amount=round(random.uniform(100, 500), 2),
            timestamp=ts,
            merchant_id=merchant_id,
            merchant_category=merchant_category,
            ip_country=random.choice(mismatched) if mismatched else "RU",
            device_id=f"dev_{fake.uuid4()[:8]}",
        )

    return build_transaction(
        user_id=user_id,
        reference_amount=round(random.uniform(2000, 10000), 2),
        timestamp=ts,
        merchant_id=merchant_id,
        merchant_category=merchant_category,
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def generate_batch(include_fraud: bool = False) -> list[dict]:
    if not include_fraud:
        return [_normal_transaction()]

    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    if pattern == "velocity":
        user_id = random.choice(_user_pool)
        base_ts = _next_timestamp()
        burst = random.randint(6, 10)
        merchant_id, merchant_category = _fraud_destination()
        return [
            _normal_transaction(
                user_id,
                timestamp=base_ts + timedelta(seconds=i),
                merchant_id=merchant_id,
                merchant_category=merchant_category,
            )
            for i in range(burst)
        ]
    return [_fraud_transaction()]


def main():
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    if GENERATOR_LIVE:
        logger.info(
            "Generator started (live) — topic=%s, rate=%s-%s/s, fraud_rate=%s",
            TOPIC_RAW,
            RATE_MIN,
            RATE_MAX,
            FRAUD_RATE,
        )
    else:
        logger.info(
            "Generator started (simulation) — topic=%s, window=%s → %s, target=%d tx, fraud_rate=%s",
            TOPIC_RAW,
            SIM_START.date(),
            SIM_END.date(),
            SIM_TOTAL,
            FRAUD_RATE,
        )

    count = 0
    try:
        while True:
            if not GENERATOR_LIVE and count >= SIM_TOTAL:
                logger.info(
                    "Simulation complete — published %d transactions (%s to %s)",
                    count,
                    SIM_START.date(),
                    SIM_END.date(),
                )
                break

            include_fraud = random.random() < FRAUD_RATE
            batch = generate_batch(include_fraud)

            for txn in batch:
                producer.produce(
                    TOPIC_RAW,
                    key=txn["user_id"].encode("utf-8"),
                    value=json.dumps(txn).encode("utf-8"),
                )
                count += 1

            producer.poll(0)

            if count % 100 == 0:
                logger.info("Published %d transactions", count)

            if GENERATOR_LIVE:
                time.sleep(1.0 / random.uniform(RATE_MIN, RATE_MAX))
            elif SIM_SLEEP_SEC > 0:
                time.sleep(SIM_SLEEP_SEC)
    except KeyboardInterrupt:
        logger.info("Generator stopped after %d transactions", count)
    finally:
        producer.flush()


if __name__ == "__main__":
    main()

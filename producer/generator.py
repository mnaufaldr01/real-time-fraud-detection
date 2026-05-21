"""Synthetic transaction generator with fraud pattern injection."""

import json
import logging
import os
import random
import time
from confluent_kafka import Producer
from dotenv import load_dotenv
from faker import Faker

from shared.fx import assign_currency, country_for_currency
from shared.synthetic import build_transaction

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
RATE_MIN = float(os.getenv("GENERATOR_RATE_MIN", "1"))
RATE_MAX = float(os.getenv("GENERATOR_RATE_MAX", "5"))
FRAUD_RATE = float(os.getenv("FRAUD_INJECTION_RATE", "0.03"))

_user_pool: list[str] = [f"user_{i:05d}" for i in range(500)]


def _normal_transaction(user_id: str | None = None) -> dict:
    from datetime import datetime, timezone

    uid = user_id or random.choice(_user_pool)
    reference = round(random.lognormvariate(3.5, 0.8), 2)
    return build_transaction(
        user_id=uid,
        reference_amount=reference,
        timestamp=datetime.now(timezone.utc),
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def _fraud_transaction() -> dict:
    """Inject one of several fraud patterns (reference amounts in USD scale)."""
    from datetime import datetime, timezone

    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    user_id = random.choice(_user_pool)
    now = datetime.now(timezone.utc)

    if pattern == "velocity":
        return build_transaction(
            user_id=user_id,
            reference_amount=round(random.uniform(20, 100), 2),
            timestamp=now,
            device_id=f"dev_{fake.uuid4()[:8]}",
        )

    if pattern == "geo_mismatch":
        currency = assign_currency(user_id)
        country = country_for_currency(currency, user_id)
        mismatched = [c for c in ("US", "GB", "DE", "FR", "AU", "SG", "ID") if c != country]
        return build_transaction(
            user_id=user_id,
            reference_amount=round(random.uniform(100, 500), 2),
            timestamp=now,
            ip_country=random.choice(mismatched) if mismatched else "RU",
            device_id=f"dev_{fake.uuid4()[:8]}",
        )

    return build_transaction(
        user_id=user_id,
        reference_amount=round(random.uniform(2000, 10000), 2),
        timestamp=now,
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def generate_batch(include_fraud: bool = False) -> list[dict]:
    if not include_fraud:
        return [_normal_transaction()]

    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    if pattern == "velocity":
        user_id = random.choice(_user_pool)
        return [_normal_transaction(user_id) for _ in range(random.randint(6, 10))]
    return [_fraud_transaction()]


def main():
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    logger.info(
        "Generator started — topic=%s, rate=%s-%s/s, fraud_rate=%s",
        TOPIC_RAW,
        RATE_MIN,
        RATE_MAX,
        FRAUD_RATE,
    )

    count = 0
    try:
        while True:
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

            rate = random.uniform(RATE_MIN, RATE_MAX)
            time.sleep(1.0 / rate)
    except KeyboardInterrupt:
        logger.info("Generator stopped after %d transactions", count)
    finally:
        producer.flush()


if __name__ == "__main__":
    main()

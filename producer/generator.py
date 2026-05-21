"""Synthetic transaction generator with fraud pattern injection."""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer
from dotenv import load_dotenv
from faker import Faker

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
RATE_MIN = float(os.getenv("GENERATOR_RATE_MIN", "1"))
RATE_MAX = float(os.getenv("GENERATOR_RATE_MAX", "5"))
FRAUD_RATE = float(os.getenv("FRAUD_INJECTION_RATE", "0.03"))

MERCHANT_CATEGORIES = [
    "5411", "5812", "5912", "4121", "5999", "5541", "6011", "7011", "7832", "7995"
]
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "JP", "SG", "NL", "ES"]
PAYMENT_METHODS = ["card", "wallet", "bank_transfer"]

# Track users for velocity fraud injection
_user_pool: list[str] = [f"user_{i:05d}" for i in range(500)]


def _normal_transaction(user_id: str | None = None) -> dict:
    country = random.choice(COUNTRIES)
    return {
        "schema_version": "1.0",
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id or random.choice(_user_pool),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": round(random.lognormvariate(3.5, 0.8), 2),
        "currency": "USD",
        "merchant_id": f"m_{fake.uuid4()[:8]}",
        "merchant_category": random.choice(MERCHANT_CATEGORIES),
        "country": country,
        "payment_method": random.choice(PAYMENT_METHODS),
        "device_id": f"dev_{fake.uuid4()[:8]}",
        "ip_country": country,
    }


def _fraud_transaction() -> dict:
    """Inject one of several fraud patterns."""
    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    user_id = random.choice(_user_pool)

    if pattern == "velocity":
        # Return burst of transactions for same user (caller handles burst)
        txn = _normal_transaction(user_id)
        txn["amount"] = round(random.uniform(20, 100), 2)
        return txn

    if pattern == "geo_mismatch":
        txn = _normal_transaction(user_id)
        txn["country"] = "US"
        txn["ip_country"] = random.choice([c for c in COUNTRIES if c != "US"])
        txn["amount"] = round(random.uniform(100, 500), 2)
        return txn

    # high_amount
    txn = _normal_transaction(user_id)
    txn["amount"] = round(random.uniform(2000, 10000), 2)
    return txn


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

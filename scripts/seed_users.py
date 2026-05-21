"""Optional warm-start: publish baseline transactions for a subset of users."""

import json
import logging
import os
import random
from datetime import datetime, timedelta, timezone

from confluent_kafka import Producer
from dotenv import load_dotenv

from shared.synthetic import MERCHANT_CATEGORIES, build_transaction

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")


def seed_user(producer: Producer, user_id: str, n_tx: int = 10):
    base = datetime.now(timezone.utc) - timedelta(days=14)
    merchants = [f"m_seed_{random.randint(1000, 9999)}" for _ in range(3)]

    for i in range(n_tx):
        txn = build_transaction(
            user_id=user_id,
            reference_amount=round(random.uniform(10, 200), 2),
            timestamp=base + timedelta(hours=i * 12),
            merchant_id=random.choice(merchants),
            merchant_category=random.choice(MERCHANT_CATEGORIES),
            payment_method="card",
            device_id=f"dev_seed_{user_id}",
        )
        producer.produce(TOPIC_RAW, key=user_id.encode(), value=json.dumps(txn).encode())


def main():
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    users = [f"user_{i:05d}" for i in range(20)]

    for user_id in users:
        seed_user(producer, user_id)

    producer.flush()
    logger.info("Seeded %d users with baseline transactions", len(users))


if __name__ == "__main__":
    main()

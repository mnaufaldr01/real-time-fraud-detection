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
from shared.synthetic import (
    HighAmountMerchantProfile,
    build_transaction,
    pick_fraud_destination,
    pick_high_amount_fraud_destination,
    pick_high_rate_fraud_destination,
    pick_high_rate_legit_destination,
)

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

# Share of non-fraud txns routed to high-rate merchants (weighted per merchant).
HIGH_RATE_LEGIT_SHARE = float(os.getenv("GENERATOR_HIGH_RATE_LEGIT_SHARE", "0.03"))
# Share of geo-mismatch fraud routed to high-rate merchants (weighted per merchant).
HIGH_RATE_GEO_FRAUD_SHARE = float(os.getenv("GENERATOR_HIGH_RATE_GEO_FRAUD_SHARE", "0.65"))

_GEO_MISMATCH_COUNTRIES = ("US", "GB", "DE", "FR", "AU", "SG", "ID")


def _velocity_burst_timestamps(base_ts: datetime, count: int) -> list[datetime]:
    """Spread a velocity burst within 0–5s using sub-second gaps (ms precision)."""
    if count <= 1:
        return [base_ts]

    gaps = [random.uniform(0.05, 1.75) for _ in range(count - 1)]
    total = sum(gaps)
    max_span = random.uniform(2.5, 5.0)
    if total > max_span:
        scale = max_span / total
        gaps = [g * scale for g in gaps]

    offsets = [0.0]
    for gap in gaps:
        offsets.append(offsets[-1] + gap)

    return [
        base_ts + timedelta(microseconds=int(round(offset * 1_000_000)))
        for offset in offsets
    ]


def _pick_merchant_for_legit_txn() -> tuple[str | None, str | None]:
    if random.random() < HIGH_RATE_LEGIT_SHARE:
        return pick_high_rate_legit_destination()
    return None, None


def _pick_merchant_for_geo_fraud() -> tuple[str, str]:
    if random.random() < HIGH_RATE_GEO_FRAUD_SHARE:
        return pick_high_rate_fraud_destination()
    if random.random() < 0.85:
        return pick_fraud_destination()
    return f"m_{fake.uuid4()[:8]}", random.choice(("7995", "6011", "5999", "5541"))


def _pick_merchant_for_velocity_fraud() -> tuple[str, str]:
    """Velocity bursts stay off high-rate merchants so their fraud % stays differentiated."""
    if random.random() < 0.85:
        return pick_fraud_destination()
    return f"m_{fake.uuid4()[:8]}", random.choice(("7995", "6011", "5999", "5541"))


def _mismatched_ip_country(user_id: str) -> str:
    currency = assign_currency(user_id)
    country = country_for_currency(currency, user_id)
    mismatched = [c for c in _GEO_MISMATCH_COUNTRIES if c != country]
    return random.choice(mismatched) if mismatched else "RU"


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
    if merchant_id is None:
        merchant_id, merchant_category = _pick_merchant_for_legit_txn()
    return build_transaction(
        user_id=uid,
        reference_amount=reference,
        timestamp=timestamp or _next_timestamp(),
        merchant_id=merchant_id,
        merchant_category=merchant_category,
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def _high_amount_fraud_transaction(
    profile: HighAmountMerchantProfile,
    timestamp: datetime | None = None,
) -> dict:
    """Large payout + geo mismatch → tier block (is_fraud=true) for amount dashboards."""
    user_id = random.choice(_user_pool)
    ts = timestamp or _next_timestamp()
    return build_transaction(
        user_id=user_id,
        reference_amount=round(random.uniform(profile.min_usd, profile.max_usd), 2),
        timestamp=ts,
        merchant_id=profile.merchant_id,
        merchant_category=profile.category,
        ip_country=_mismatched_ip_country(user_id),
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def _geo_mismatch_fraud_transaction(timestamp: datetime | None = None) -> dict:
    user_id = random.choice(_user_pool)
    ts = timestamp or _next_timestamp()
    merchant_id, merchant_category = _pick_merchant_for_geo_fraud()
    return build_transaction(
        user_id=user_id,
        reference_amount=round(random.uniform(100, 500), 2),
        timestamp=ts,
        merchant_id=merchant_id,
        merchant_category=merchant_category,
        ip_country=_mismatched_ip_country(user_id),
        device_id=f"dev_{fake.uuid4()[:8]}",
    )


def _fraud_transaction(timestamp: datetime | None = None) -> dict:
    """Inject one of several fraud patterns (reference amounts in USD scale)."""
    pattern = random.choice(["velocity", "geo_mismatch", "high_amount"])
    if pattern == "high_amount":
        return _high_amount_fraud_transaction(pick_high_amount_fraud_destination(), timestamp)
    if pattern == "geo_mismatch":
        return _geo_mismatch_fraud_transaction(timestamp)

    user_id = random.choice(_user_pool)
    ts = timestamp or _next_timestamp()
    merchant_id, merchant_category = _pick_merchant_for_velocity_fraud()
    return build_transaction(
        user_id=user_id,
        reference_amount=round(random.uniform(20, 100), 2),
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
        merchant_id, merchant_category = _pick_merchant_for_velocity_fraud()
        timestamps = _velocity_burst_timestamps(base_ts, burst)
        return [
            _normal_transaction(
                user_id,
                timestamp=timestamps[i],
                merchant_id=merchant_id,
                merchant_category=merchant_category,
            )
            for i in range(burst)
        ]
    if pattern == "high_amount":
        return [_high_amount_fraud_transaction(pick_high_amount_fraud_destination())]
    return [_geo_mismatch_fraud_transaction()]


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
            "Generator started (simulation) — topic=%s, window=%s → %s, "
            "target=%d tx, fraud_rate=%s",
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

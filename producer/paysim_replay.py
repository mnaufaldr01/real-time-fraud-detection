"""Replay PaySim CSV to Kafka as multi-currency TransactionEvents."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import time
from pathlib import Path

from confluent_kafka import Producer
from dotenv import load_dotenv

from shared.paysim_transform import transform_row_with_label

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = (
    PROJECT_ROOT / "producer" / "sample_dataset" / "PS_20174392719_1491204439457_log.csv"
)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")


def replay(
    csv_path: Path,
    *,
    limit: int | None = None,
    sample_rate: float = 1.0,
    rate: float | None = None,
    labels_out: Path | None = None,
) -> int:
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    labels_file = labels_out.open("w", encoding="utf-8", newline="") if labels_out else None
    labels_writer = csv.writer(labels_file) if labels_file else None
    if labels_writer:
        labels_writer.writerow(["transaction_id", "is_fraud"])

    published = 0
    skipped = 0
    interval = 1.0 / rate if rate and rate > 0 else 0.0
    last_publish = time.perf_counter()

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if limit is not None and published >= limit:
                break
            if sample_rate < 1.0 and random.random() > sample_rate:
                continue

            event, is_fraud = transform_row_with_label(row)
            if event is None:
                skipped += 1
                continue

            producer.produce(
                TOPIC_RAW,
                key=event["user_id"].encode("utf-8"),
                value=json.dumps(event).encode("utf-8"),
            )
            producer.poll(0)

            if labels_writer:
                labels_writer.writerow([event["transaction_id"], is_fraud])

            published += 1
            if published % 10_000 == 0:
                logger.info("Published %d events (skipped %d)", published, skipped)

            if interval > 0:
                elapsed = time.perf_counter() - last_publish
                if elapsed < interval:
                    time.sleep(interval - elapsed)
                last_publish = time.perf_counter()

    producer.flush()
    if labels_file:
        labels_file.close()

    logger.info(
        "Replay complete: published=%d skipped=%d topic=%s",
        published,
        skipped,
        TOPIC_RAW,
    )
    return published


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay PaySim CSV to Kafka")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(os.getenv("PAYSIM_CSV", str(DEFAULT_CSV))),
        help="Path to PaySim CSV",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max rows to publish")
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=1.0,
        help="Random subsample fraction (0-1)",
    )
    parser.add_argument("--rate", type=float, default=None, help="Max events per second")
    parser.add_argument(
        "--labels-out",
        type=Path,
        default=None,
        help="Optional sidecar CSV: transaction_id,is_fraud",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    replay(
        args.csv,
        limit=args.limit,
        sample_rate=args.sample_rate,
        rate=args.rate,
        labels_out=args.labels_out,
    )


if __name__ == "__main__":
    main()

"""Kafka fraud scoring consumer entry point."""

import json
import logging
import signal
import time
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaError, Producer

from consumer.anomaly import compute_anomaly_score
from consumer.config import config
from consumer.rules import evaluate_rules
from consumer.scoring import compute_final_score
from consumer.sink import FraudSink
from consumer.validate import validate_event
from shared.fx import to_usd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("fraud_consumer")

_running = True


def _json_log(**kwargs):
    logger.info(json.dumps(kwargs))


def publish_dlq(producer: Producer, original: dict | None, error_code: str, error_message: str):
    payload = {
        "original_payload": original,
        "error_code": error_code,
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    producer.produce(
        config.topic_dlq,
        value=json.dumps(payload).encode("utf-8"),
    )
    producer.poll(0)


def handle_message(msg_value: bytes, sink: FraudSink, dlq_producer: Producer) -> None:
    start = time.perf_counter()
    result = validate_event(msg_value)

    if not result.ok:
        publish_dlq(dlq_producer, result.raw_payload, result.error_code, result.error_message)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _json_log(event="dlq", error_code=result.error_code, latency_ms=latency_ms)
        return

    event = result.event
    try:
        amount_usd = to_usd(event.amount, event.currency)
    except ValueError as exc:
        publish_dlq(dlq_producer, result.raw_payload, "FX_CONVERSION", str(exc))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _json_log(event="dlq", error_code="FX_CONVERSION", latency_ms=latency_ms)
        return

    ts = event.timestamp
    now = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    stats = sink.load_user_stats(event.user_id, event.merchant_id, now)
    user_mean, user_std = sink.load_user_amount_stats(event.user_id)

    rule_result = evaluate_rules(event, stats, amount_usd=amount_usd)
    anomaly_score = compute_anomaly_score(
        event, user_mean, user_std, amount_usd=amount_usd
    )
    score = compute_final_score(rule_result, anomaly_score)

    sink.persist(event, score, amount_usd=amount_usd)

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    _json_log(
        event="scored",
        transaction_id=str(event.transaction_id),
        rule_score=score.rule_score,
        anomaly_score=score.anomaly_score,
        final_score=score.final_score,
        is_fraud=score.is_fraud,
        flag_reasons=score.flag_reasons,
        latency_ms=latency_ms,
    )


def main():
    global _running

    def shutdown(signum, frame):
        global _running
        _running = False
        logger.info("Shutting down consumer...")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    consumer = Consumer(
        {
            "bootstrap.servers": config.kafka_bootstrap,
            "group.id": config.consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    dlq_producer = Producer({"bootstrap.servers": config.kafka_bootstrap})
    sink = FraudSink()

    consumer.subscribe([config.topic_raw])
    logger.info("Consumer started on topic %s (group=%s)", config.topic_raw, config.consumer_group)

    try:
        while _running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error: %s", msg.error())
                continue

            try:
                handle_message(msg.value(), sink, dlq_producer)
            except Exception as exc:
                logger.exception("Failed to process message: %s", exc)
                try:
                    raw = json.loads(msg.value().decode("utf-8"))
                except Exception:
                    raw = {"raw": msg.value().decode("utf-8", errors="replace")}
                publish_dlq(dlq_producer, raw, "PROCESSING_ERROR", str(exc))
    finally:
        sink.flush()
        dlq_producer.flush()
        consumer.close()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    main()

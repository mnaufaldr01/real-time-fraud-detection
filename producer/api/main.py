"""FastAPI ingestion endpoint for manual transaction submission."""

import json
import logging
import os

from confluent_kafka import Producer
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from shared.schema import TransactionEvent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")

app = FastAPI(title="Fraud Detection Ingestion API", version="1.0.0")
producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transactions", status_code=202)
def post_transaction(event: TransactionEvent):
    payload = event.model_dump(mode="json")
    payload["timestamp"] = event.timestamp.isoformat()

    try:
        producer.produce(
            TOPIC_RAW,
            key=event.user_id.encode("utf-8"),
            value=json.dumps(payload).encode("utf-8"),
        )
        producer.flush(timeout=5)
    except Exception as exc:
        logger.exception("Failed to publish to Kafka")
        raise HTTPException(status_code=503, detail=f"Kafka publish failed: {exc}") from exc

    return {
        "status": "accepted",
        "transaction_id": str(event.transaction_id),
        "topic": TOPIC_RAW,
    }

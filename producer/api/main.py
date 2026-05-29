"""FastAPI ingestion endpoint for manual transaction submission."""

import json
import logging
import os
from uuid import UUID

from confluent_kafka import Producer
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine

from shared.schema import TransactionEvent
from shared.transaction_delete import delete_transaction_cascade

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://fraud:fraud@localhost:5433/fraud_db"
)

app = FastAPI(title="Fraud Detection Ingestion API", version="1.0.0")
producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
_db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)


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


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: UUID):
    """Remove a transaction and all related rows (risk_scores, fraud_flags, history)."""
    try:
        deleted = delete_transaction_cascade(_db_engine, transaction_id)
    except Exception as exc:
        logger.exception("Failed to delete transaction %s", transaction_id)
        raise HTTPException(status_code=503, detail=f"Database delete failed: {exc}") from exc

    if deleted is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    logger.info("Deleted transaction %s: %s", transaction_id, deleted)
    return {
        "status": "deleted",
        "transaction_id": str(transaction_id),
        "deleted_rows": deleted,
    }

"""PaySim CSV row → TransactionEvent dict for Kafka replay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.fx import (
    BASE_CURRENCY,
    assign_currency,
    country_for_currency,
    local_amount_from_reference,
)

BASE_TIME = datetime(2017, 1, 1, tzinfo=timezone.utc)

TYPE_TO_PAYMENT = {
    "PAYMENT": "card",
    "DEBIT": "card",
    "TRANSFER": "bank_transfer",
    "CASH_IN": "bank_transfer",
    "CASH_OUT": "bank_transfer",
}

TYPE_TO_MCC = {
    "PAYMENT": "5999",
    "DEBIT": "6011",
    "TRANSFER": "6012",
    "CASH_IN": "6011",
    "CASH_OUT": "6011",
}


def transform_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Map one PaySim row to a Kafka-ready event dict, or None if filtered out."""
    amount_ref = float(row["amount"])
    if amount_ref <= 0:
        return None

    user_id = str(row["nameOrig"])
    tx_type = str(row["type"])
    currency = assign_currency(user_id)

    if currency == BASE_CURRENCY:
        amount = amount_ref
    else:
        amount = local_amount_from_reference(amount_ref, currency)

    country = country_for_currency(currency, user_id)
    timestamp = BASE_TIME + timedelta(hours=int(row["step"]))

    return {
        "schema_version": "1.0",
        "transaction_id": str(uuid4()),
        "user_id": user_id,
        "timestamp": timestamp.isoformat(),
        "amount": amount,
        "currency": currency,
        "merchant_id": str(row["nameDest"]),
        "merchant_category": TYPE_TO_MCC.get(tx_type, "5999"),
        "country": country,
        "payment_method": TYPE_TO_PAYMENT.get(tx_type, "card"),
        "device_id": None,
        "ip_country": country,
    }


def transform_row_with_label(row: dict[str, Any]) -> tuple[Optional[dict[str, Any]], int]:
    """Return (event_dict, is_fraud) for optional offline label sidecar."""
    event = transform_row(row)
    is_fraud = int(row.get("isFraud", 0))
    return event, is_fraud

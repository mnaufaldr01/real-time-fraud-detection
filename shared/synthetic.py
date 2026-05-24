"""Unified synthetic TransactionEvent builder for generator, seed, and profiling."""

from __future__ import annotations

import random
import uuid
from datetime import datetime
from typing import Any, Optional

from shared.fx import (
    BASE_CURRENCY,
    assign_currency,
    country_for_currency,
    local_amount_from_reference,
    to_usd,
)

MERCHANT_CATEGORIES = [
    "5411",
    "5812",
    "5912",
    "4121",
    "5999",
    "5541",
    "6011",
    "7011",
    "7832",
    "7995",
]

PAYMENT_METHODS = ["card", "wallet", "bank_transfer"]

# High-risk merchants that concentrate synthetic fraud payouts (generator / profiling).
FRAUD_DESTINATION_MERCHANTS: tuple[tuple[str, str], ...] = (
    ("m_fraud_dest_wirex", "7995"),
    ("m_fraud_dest_fastpay", "6011"),
    ("m_fraud_dest_offshore_gaming", "7995"),
    ("m_fraud_dest_crypto_swap", "6011"),
    ("m_fraud_dest_lux_reseller", "5999"),
    ("m_fraud_dest_anonymous_gift", "5999"),
)


def pick_fraud_destination() -> tuple[str, str]:
    """Return (merchant_id, merchant_category) for a fraud payout destination."""
    return random.choice(FRAUD_DESTINATION_MERCHANTS)


def build_transaction(
    *,
    user_id: str,
    reference_amount: float,
    timestamp: datetime,
    merchant_id: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    device_id: Optional[str] = None,
    ip_country: Optional[str] = None,
) -> dict[str, Any]:
    """Build a Kafka-ready event with local currency amount (no USD on wire)."""
    currency = assign_currency(user_id)
    if currency == BASE_CURRENCY:
        amount = round(reference_amount, 2)
    else:
        amount = local_amount_from_reference(reference_amount, currency)

    country = country_for_currency(currency, user_id)
    if ip_country is None:
        ip_country = country

    return {
        "schema_version": "1.0",
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "timestamp": timestamp.isoformat(),
        "amount": amount,
        "currency": currency,
        "merchant_id": merchant_id or f"m_{uuid.uuid4().hex[:8]}",
        "merchant_category": merchant_category or random.choice(MERCHANT_CATEGORIES),
        "country": country,
        "payment_method": payment_method or random.choice(PAYMENT_METHODS),
        "device_id": device_id,
        "ip_country": ip_country,
    }


def reference_amount_usd(txn: dict[str, Any]) -> float:
    """Compute USD equivalent for profiling (mirrors consumer to_usd)."""
    return to_usd(float(txn["amount"]), str(txn["currency"]))

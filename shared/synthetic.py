"""Unified synthetic TransactionEvent builder for generator, seed, and profiling."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
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

# Dashboard: top fraud payout merchants by USD amount (high_amount + geo hard-decline).
@dataclass(frozen=True)
class HighAmountMerchantProfile:
    merchant_id: str
    category: str
    min_usd: float
    max_usd: float


HIGH_AMOUNT_MERCHANT_PROFILES: tuple[HighAmountMerchantProfile, ...] = (
    HighAmountMerchantProfile("m_fraud_dest_wirex", "7995", 18_000, 28_000),
    HighAmountMerchantProfile("m_fraud_dest_offshore_gaming", "7995", 12_000, 20_000),
    HighAmountMerchantProfile("m_fraud_dest_crypto_swap", "6011", 8_000, 15_000),
)

# Dashboard: merchants with different fraud-rate targets (~15%, ~22%, ~38%).
@dataclass(frozen=True)
class HighRateMerchantProfile:
    merchant_id: str
    category: str
    legit_weight: float
    fraud_weight: float


HIGH_RATE_MERCHANT_PROFILES: tuple[HighRateMerchantProfile, ...] = (
    HighRateMerchantProfile("m_fraud_dest_fastpay", "6011", 6.0, 1.0),
    HighRateMerchantProfile("m_fraud_dest_lux_reseller", "5999", 3.5, 1.6),
    HighRateMerchantProfile("m_fraud_dest_anonymous_gift", "5999", 2.0, 2.8),
)

# Backward-compatible tuples for callers that only need id + category.
HIGH_AMOUNT_FRAUD_MERCHANTS: tuple[tuple[str, str], ...] = tuple(
    (p.merchant_id, p.category) for p in HIGH_AMOUNT_MERCHANT_PROFILES
)
HIGH_RATE_FRAUD_MERCHANTS: tuple[tuple[str, str], ...] = tuple(
    (p.merchant_id, p.category) for p in HIGH_RATE_MERCHANT_PROFILES
)


def pick_fraud_destination() -> tuple[str, str]:
    """Return (merchant_id, merchant_category) for a fraud payout destination."""
    return random.choice(FRAUD_DESTINATION_MERCHANTS)


def pick_high_amount_fraud_destination() -> HighAmountMerchantProfile:
    return random.choice(HIGH_AMOUNT_MERCHANT_PROFILES)


def pick_high_rate_fraud_destination() -> tuple[str, str]:
    profile = _weighted_high_rate_profile("fraud")
    return profile.merchant_id, profile.category


def pick_high_rate_legit_destination() -> tuple[str, str]:
    profile = _weighted_high_rate_profile("legit")
    return profile.merchant_id, profile.category


def _weighted_high_rate_profile(mode: str) -> HighRateMerchantProfile:
    weights = [
        p.fraud_weight if mode == "fraud" else p.legit_weight
        for p in HIGH_RATE_MERCHANT_PROFILES
    ]
    return random.choices(HIGH_RATE_MERCHANT_PROFILES, weights=weights, k=1)[0]


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

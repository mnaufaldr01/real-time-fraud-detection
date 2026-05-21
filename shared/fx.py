"""Static FX rates and currency assignment for multi-currency transactions.

Rate convention: FX_RATES[currency] = USD per 1 unit of that currency.
Consumer scoring uses to_usd(); publishers use local_amount_from_reference()
only to fabricate local denominations (not for fraud detection).
"""

from __future__ import annotations

import hashlib

BASE_CURRENCY = "USD"

SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"USD", "GBP", "AUD", "SGD", "IDR", "EUR"})

# Approximate mid-2024 rates: USD per 1 unit of foreign currency
FX_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "AUD": 0.65,
    "SGD": 0.74,
    "IDR": 0.000063,
}

# Weighted currency mix (must sum to 100)
CURRENCY_WEIGHTS: list[tuple[str, int]] = [
    ("USD", 55),
    ("EUR", 15),
    ("GBP", 10),
    ("AUD", 8),
    ("SGD", 7),
    ("IDR", 5),
]

CURRENCY_COUNTRY: dict[str, str] = {
    "USD": "US",
    "GBP": "GB",
    "AUD": "AU",
    "SGD": "SG",
    "IDR": "ID",
}

EUR_COUNTRIES = ("DE", "FR", "NL")


def _user_bucket(user_id: str) -> int:
    digest = hashlib.sha256(user_id.encode()).hexdigest()
    return int(digest[:8], 16) % 100


def assign_currency(user_id: str) -> str:
    """Deterministic currency assignment from user_id (same user → same currency)."""
    bucket = _user_bucket(user_id)
    cumulative = 0
    for currency, weight in CURRENCY_WEIGHTS:
        cumulative += weight
        if bucket < cumulative:
            return currency
    return "USD"


def country_for_currency(currency: str, user_id: str) -> str:
    """Primary ISO-2 country for a currency; EUR varies by user hash."""
    if currency == "EUR":
        idx = _user_bucket(user_id + ":eur") % len(EUR_COUNTRIES)
        return EUR_COUNTRIES[idx]
    return CURRENCY_COUNTRY.get(currency, "US")


def to_usd(amount: float, currency: str) -> float:
    """Convert local amount to USD (consumer scoring path)."""
    code = currency.upper()
    if code not in FX_RATES:
        raise ValueError(f"Unsupported currency: {currency}")
    return round(amount * FX_RATES[code], 2)


def local_amount_from_reference(reference_usd: float, currency: str) -> float:
    """Fabricate a local denomination from a reference USD-scale amount (publishers only)."""
    code = currency.upper()
    if code not in FX_RATES:
        raise ValueError(f"Unsupported currency: {currency}")
    if code == BASE_CURRENCY:
        return round(reference_usd, 2)
    local = reference_usd / FX_RATES[code]
    if code == "IDR":
        return round(local, 0)
    return round(local, 2)

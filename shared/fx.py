"""FX rates and currency assignment for multi-currency transactions.

Rate convention: rates[currency] = USD per 1 unit of that currency.
Consumer scoring uses to_usd() with live DB snapshots; publishers use
local_amount_from_reference() with DEFAULT_FX_RATES for local denominations.
"""

from __future__ import annotations

import hashlib

BASE_CURRENCY = "USD"

SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"USD", "GBP", "AUD", "SGD", "IDR", "EUR"})

# Approximate mid-2024 rates: USD per 1 unit of foreign currency (fallback only)
DEFAULT_FX_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "AUD": 0.65,
    "SGD": 0.74,
    "IDR": 0.000063,
}

# Backward-compatible alias
FX_RATES = DEFAULT_FX_RATES

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


def merge_rates(api_rates: dict[str, float]) -> dict[str, float]:
    """Ensure every supported currency has a rate; fill gaps from DEFAULT_FX_RATES."""
    merged = dict(DEFAULT_FX_RATES)
    for code, rate in api_rates.items():
        merged[code.upper()] = rate
    return merged


def _resolve_rates(rates: dict[str, float] | None) -> dict[str, float]:
    return DEFAULT_FX_RATES if rates is None else rates


def to_usd(amount: float, currency: str, rates: dict[str, float] | None = None) -> float:
    """Convert local amount to USD (consumer scoring path)."""
    table = _resolve_rates(rates)
    code = currency.upper()
    if code not in table:
        raise ValueError(f"Unsupported currency: {currency}")
    return round(amount * table[code], 2)


def local_amount_from_reference(
    reference_usd: float,
    currency: str,
    rates: dict[str, float] | None = None,
) -> float:
    """Fabricate a local denomination from a reference USD-scale amount (publishers only)."""
    table = _resolve_rates(rates)
    code = currency.upper()
    if code not in table:
        raise ValueError(f"Unsupported currency: {currency}")
    if code == BASE_CURRENCY:
        return round(reference_usd, 2)
    local = reference_usd / table[code]
    if code == "IDR":
        return round(local, 0)
    return round(local, 2)

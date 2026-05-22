"""Unit tests for FX API client normalization."""

import pytest

from shared.fx_client import normalize_fxratesapi_response

SAMPLE_RESPONSE = {
    "success": True,
    "date": "2026-05-22T04:20:00.000Z",
    "base": "USD",
    "rates": {
        "AUD": 1.4002001886,
        "EUR": 0.8609521095,
        "GBP": 0.7445491365,
        "IDR": 17701.002223765,
        "SGD": 1.2787001882,
    },
}


def test_normalize_fxratesapi_inverts_to_usd_per_unit():
    rates = normalize_fxratesapi_response(SAMPLE_RESPONSE)
    assert rates["USD"] == 1.0
    assert rates["EUR"] == pytest.approx(1.0 / 0.8609521095, rel=1e-6)
    assert rates["GBP"] == pytest.approx(1.0 / 0.7445491365, rel=1e-6)
    assert rates["IDR"] == pytest.approx(1.0 / 17701.002223765, rel=1e-6)


def test_normalize_fxratesapi_eur_example():
    rates = normalize_fxratesapi_response(SAMPLE_RESPONSE)
    assert to_usd_equiv(100.0, "EUR", rates) == pytest.approx(116.15, abs=0.05)


def test_normalize_rejects_unsuccessful_response():
    with pytest.raises(ValueError, match="success=false"):
        normalize_fxratesapi_response({"success": False, "rates": {}})


def test_normalize_rejects_zero_rate():
    bad = {**SAMPLE_RESPONSE, "rates": {"EUR": 0.0}}
    with pytest.raises(ValueError, match="zero rate"):
        normalize_fxratesapi_response(bad)


def to_usd_equiv(amount: float, currency: str, rates: dict[str, float]) -> float:
    return round(amount * rates[currency.upper()], 2)

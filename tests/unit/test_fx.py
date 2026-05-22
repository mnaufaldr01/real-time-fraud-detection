"""Unit tests for FX conversion and currency assignment."""

import pytest

from shared.fx import (
    assign_currency,
    country_for_currency,
    local_amount_from_reference,
    to_usd,
)


def test_to_usd_usd_identity():
    assert to_usd(100.0, "USD") == 100.0


def test_to_usd_gbp():
    assert to_usd(100.0, "GBP") == 127.0


def test_to_usd_with_explicit_rates():
    rates = {"USD": 1.0, "GBP": 1.27}
    assert to_usd(100.0, "GBP", rates=rates) == 127.0


def test_local_amount_round_trip():
    reference = 9839.64
    local = local_amount_from_reference(reference, "GBP")
    assert abs(to_usd(local, "GBP") - reference) < 0.02


def test_idr_rounds_to_whole_units():
    local = local_amount_from_reference(45.0, "IDR")
    assert local == round(local, 0)


def test_assign_currency_stable():
    assert assign_currency("user_001") == assign_currency("user_001")


def test_country_for_currency_eur_varies():
    countries = {country_for_currency("EUR", f"user_{i}") for i in range(20)}
    assert countries.issubset({"DE", "FR", "NL"})
    assert len(countries) >= 2


def test_unknown_currency_raises():
    with pytest.raises(ValueError, match="Unsupported currency"):
        to_usd(100.0, "JPY")

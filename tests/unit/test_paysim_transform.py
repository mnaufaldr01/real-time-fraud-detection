"""Unit tests for PaySim row transformation."""

from shared.fx import assign_currency, country_for_currency, to_usd
from shared.paysim_transform import transform_row


def _paysim_row(**overrides):
    row = {
        "step": "1",
        "type": "PAYMENT",
        "amount": "9839.64",
        "nameOrig": "C1231006815",
        "nameDest": "M1979787155",
        "isFraud": "0",
    }
    row.update(overrides)
    return row


def test_transform_row_maps_fields():
    event = transform_row(_paysim_row())
    assert event is not None
    assert event["user_id"] == "C1231006815"
    assert event["merchant_id"] == "M1979787155"
    assert event["payment_method"] == "card"
    assert event["merchant_category"] == "5999"
    assert "transaction_id" in event
    assert "amount_usd" not in event


def test_transform_row_filters_non_positive_amount():
    assert transform_row(_paysim_row(amount="0")) is None
    assert transform_row(_paysim_row(amount="-1")) is None


def test_transform_row_currency_geo_coupling():
    event = transform_row(_paysim_row())
    currency = assign_currency(event["user_id"])
    assert event["currency"] == currency
    assert event["country"] == country_for_currency(currency, event["user_id"])


def test_transform_row_local_amount_converts_back_to_reference():
    event = transform_row(_paysim_row(amount="1000.0"))
    usd_equiv = to_usd(event["amount"], event["currency"])
    assert abs(usd_equiv - 1000.0) < 0.02

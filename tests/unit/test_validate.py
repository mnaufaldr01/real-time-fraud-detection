"""Unit tests for event validation."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from consumer.validate import validate_event


def test_valid_event():
    payload = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "user_001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": 100.0,
        "currency": "USD",
        "merchant_id": "m_001",
        "merchant_category": "5411",
        "country": "US",
        "payment_method": "card",
        "ip_country": "US",
    }
    result = validate_event(payload)
    assert result.ok is True
    assert result.event is not None


def test_negative_amount_rejected():
    payload = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "user_001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": -10.0,
        "currency": "USD",
        "merchant_id": "m_001",
        "merchant_category": "5411",
        "country": "US",
        "payment_method": "card",
        "ip_country": "US",
    }
    result = validate_event(payload)
    assert result.ok is False
    assert result.error_code == "SCHEMA_VALIDATION"


def test_missing_field_rejected():
    result = validate_event({"user_id": "user_001"})
    assert result.ok is False


def test_invalid_json_rejected():
    result = validate_event(b"not json")
    assert result.ok is False
    assert result.error_code == "INVALID_JSON"


def test_unsupported_schema_version():
    payload = {
        "schema_version": "2.0",
        "transaction_id": str(uuid.uuid4()),
        "user_id": "user_001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": 100.0,
        "currency": "USD",
        "merchant_id": "m_001",
        "merchant_category": "5411",
        "country": "US",
        "payment_method": "card",
        "ip_country": "US",
    }
    result = validate_event(payload)
    assert result.ok is False

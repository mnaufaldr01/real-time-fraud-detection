"""Pydantic validation for incoming Kafka events."""

import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import ValidationError

from shared.schema import TransactionEvent


@dataclass
class ValidationResult:
    ok: bool
    event: Optional[TransactionEvent] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None


def validate_event(raw: bytes | str | dict) -> ValidationResult:
    """Validate raw Kafka payload against TransactionEvent schema."""
    payload: dict[str, Any]
    try:
        if isinstance(raw, bytes):
            payload = json.loads(raw.decode("utf-8"))
        elif isinstance(raw, str):
            payload = json.loads(raw)
        else:
            payload = raw
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        if isinstance(raw, bytes):
            raw_text = raw.decode("utf-8", errors="replace")
        else:
            raw_text = str(raw)
        return ValidationResult(
            ok=False,
            error_code="INVALID_JSON",
            error_message=str(exc),
            raw_payload={"raw": raw_text},
        )

    try:
        event = TransactionEvent.model_validate(payload)
        return ValidationResult(ok=True, event=event, raw_payload=payload)
    except ValidationError as exc:
        return ValidationResult(
            ok=False,
            error_code="SCHEMA_VALIDATION",
            error_message=exc.errors()[0]["msg"] if exc.errors() else str(exc),
            raw_payload=payload,
        )

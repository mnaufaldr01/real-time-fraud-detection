"""Shared transaction event model used by API, consumer, and generator."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from shared.fx import SUPPORTED_CURRENCIES


class PaymentMethod(str, Enum):
    CARD = "card"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class TransactionEvent(BaseModel):
    schema_version: str = "1.0"
    transaction_id: UUID
    user_id: str
    timestamp: datetime
    amount: float = Field(gt=0)
    currency: str = "USD"
    merchant_id: str
    merchant_category: str
    country: str = Field(min_length=2, max_length=2)
    payment_method: PaymentMethod
    device_id: Optional[str] = None
    ip_country: str = Field(min_length=2, max_length=2)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        code = v.upper() if isinstance(v, str) else v
        if code not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {v}")
        return code

    @field_validator("country", "ip_country", mode="before")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.upper() if isinstance(v, str) else v

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        major = v.split(".")[0]
        if major != "1":
            raise ValueError(f"Unsupported schema major version: {major}")
        return v

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum
import re

class CurrencyEnum(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TransactionTransferRequest(BaseModel):
    source_account: str = Field(
        ..., 
        description="Origin account ID", 
        pattern=r"^acc_[a-zA-Z0-9]{8,16}$"
    )
    destination_account: str = Field(
        ..., 
        description="Destination account ID", 
        pattern=r"^acc_[a-zA-Z0-9]{8,16}$"
    )
    amount_cents: int = Field(
        ..., 
        gt=0, 
        le=5_000_000, 
        description="Transfer amount in cents (Max $50,000.00)"
    )
    currency: CurrencyEnum = Field(
        default=CurrencyEnum.USD, 
        description="Standard 3-letter currency code"
    )
    audit_reason: str = Field(
        ..., 
        min_length=10, 
        max_length=255, 
        description="Business context for transfer audit log"
    )

    @field_validator("destination_account")
    def prevent_self_transfer(cls, v, values):
        if "source_account" in values.data and v == values.data["source_account"]:
            raise ValueError("Destination account cannot match source account.")
        return v

class TransactionTransferResponse(BaseModel):
    transaction_id: str
    status: str
    debited_cents: int
    fee_cents: int
    authorized: bool
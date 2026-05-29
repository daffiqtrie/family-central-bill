"""Pydantic schemas for bill checking requests and responses."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderEnum(str, Enum):
    """Supported utility providers for bill checking."""

    PLN = "PLN"
    PDAM = "PDAM"
    INDIHOME = "INDIHOME"


class BillStatus(str, Enum):
    """Bill payment status."""

    UNPAID = "UNPAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class BillCheckRequest(BaseModel):
    """Request schema for checking a bill."""

    @field_validator("customer_id")
    @classmethod
    def normalize_customer_id(cls, value: str) -> str:
        """Normalize and validate a customer ID before provider calls."""
        normalized = value.strip()
        if not normalized.isdecimal():
            raise ValueError("Customer ID must contain digits only")
        return normalized

    provider: ProviderEnum = Field(
        ...,
        description="Utility provider to check",
    )
    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Customer ID from the utility provider",
    )


class BillPeriod(BaseModel):
    """Represents a billing period."""

    month: int = Field(..., ge=1, le=12, description="Billing month (1-12)")
    year: int = Field(..., ge=2000, le=2100, description="Billing year")

    @property
    def display(self) -> str:
        """Human-readable period string."""
        months = [
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        ]
        return f"{months[self.month - 1]} {self.year}"


class BillDetail(BaseModel):
    """Detailed bill information for a single period."""

    period: BillPeriod
    amount: Decimal = Field(..., description="Bill amount in IDR")
    admin_fee: Decimal = Field(default=Decimal("2500"), description="Admin fee in IDR")

    @property
    def total(self) -> Decimal:
        """Total amount including admin fee."""
        return self.amount + self.admin_fee


class BillCheckResponse(BaseModel):
    """Response schema for bill checking result."""

    model_config = ConfigDict(from_attributes=True)

    provider: ProviderEnum = Field(..., description="Utility provider")
    customer_id: str = Field(..., description="Customer ID")
    customer_name: str = Field(..., description="Customer name from provider")
    status: BillStatus = Field(..., description="Bill status")

    # Bill details (nullable if status is NOT_FOUND or ERROR)
    bills: list[BillDetail] = Field(
        default_factory=list,
        description="List of unpaid bills",
    )
    total_amount: Decimal = Field(
        default=Decimal("0"),
        description="Total amount due including fees",
    )
    due_date: date | None = Field(
        default=None,
        description="Payment due date",
    )

    # Provider-specific metadata
    meter_number: str | None = Field(
        default=None, description="Meter/connection number"
    )
    tariff_class: str | None = Field(default=None, description="Tariff class/category")
    power_rating: str | None = Field(
        default=None, description="Power rating (PLN only)"
    )

    # Metadata
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the check was performed",
    )
    message: str | None = Field(
        default=None,
        description="Additional message or error details",
    )


class BillCheckError(BaseModel):
    """Error response for bill checking failures."""

    provider: ProviderEnum
    customer_id: str
    status: BillStatus = BillStatus.ERROR
    message: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

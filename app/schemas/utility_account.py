"""Pydantic schemas for UtilityAccount requests and responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProviderEnum(str, Enum):
    """Supported utility providers."""
    
    PLN = "PLN"
    PDAM = "PDAM"
    INDIHOME = "INDIHOME"


class UtilityAccountBase(BaseModel):
    """Base schema with shared fields."""
    
    provider: ProviderEnum = Field(
        ...,
        description="Utility provider (PLN, PDAM, INDIHOME)",
    )
    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Customer ID from the utility provider",
    )
    alias: str | None = Field(
        default=None,
        max_length=100,
        description="Human-readable name for this account",
    )


class UtilityAccountCreate(UtilityAccountBase):
    """Schema for creating a new utility account."""
    
    is_active: bool = Field(
        default=True,
        description="Whether this account is actively tracked",
    )


class UtilityAccountUpdate(BaseModel):
    """Schema for updating an existing utility account (partial update)."""
    
    provider: ProviderEnum | None = None
    customer_id: str | None = Field(default=None, min_length=1, max_length=50)
    alias: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class UtilityAccountResponse(UtilityAccountBase):
    """Schema for utility account API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    is_active: bool = Field(..., description="Whether this account is actively tracked")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

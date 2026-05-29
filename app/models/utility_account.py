"""UtilityAccount model for managing household utility accounts."""

from enum import Enum

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ProviderEnum(str, Enum):
    """Supported utility providers."""
    
    PLN = "PLN"           # Electricity
    PDAM = "PDAM"         # Water
    INDIHOME = "INDIHOME" # Internet


class UtilityAccount(Base):
    """
    Represents a household utility account.
    
    Attributes:
        id: Primary key
        provider: Utility provider (PLN, PDAM, INDIHOME)
        customer_id: Unique customer identifier from the provider
        alias: Human-readable name for the account (optional)
        is_active: Whether the account is actively being tracked
    """

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    provider: Mapped[ProviderEnum] = mapped_column(
        SQLEnum(ProviderEnum, native_enum=False, length=20),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    alias: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<UtilityAccount(id={self.id}, provider={self.provider.value}, "
            f"customer_id='{self.customer_id}')>"
        )

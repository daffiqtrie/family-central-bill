"""Bill cache model for smart caching of bill check results."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class BillCache(Base):
    """
    Cache for bill check results.
    
    Stores the latest successful fetch result to avoid hitting
    the scraper API too frequently.
    
    TTL: 12 hours (configured in orchestrator)
    """
    
    __tablename__ = "bill_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Composite key for cache lookup
    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Cached bill data
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Period info (format: "MM/YYYY" or "MM/YYYY,MM/YYYY" for multiple)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Total amount in rupiah (as integer for precision)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Full response JSON for reconstruction
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Cache metadata
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now()
    )
    
    # Composite index for efficient lookup
    __table_args__ = (
        Index("ix_bill_cache_provider_customer", "provider", "customer_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<BillCache {self.provider}:{self.customer_id} amount={self.amount}>"
    
    @classmethod
    def from_response(
        cls,
        provider: str,
        customer_id: str,
        customer_name: str,
        status: str,
        amount: int,
        period: str | None = None,
        response_json: str | None = None,
    ) -> "BillCache":
        """Create a BillCache instance from bill check response data."""
        return cls(
            provider=provider,
            customer_id=customer_id,
            customer_name=customer_name,
            status=status,
            amount=amount,
            period=period,
            response_json=response_json,
        )

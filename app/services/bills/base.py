"""Abstract base class for bill checking services.

This module defines the interface that all bill checker implementations
must follow, enabling easy swapping between mock/simulation and real
scraping implementations.
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from app.schemas.bill import BillCheckResponse


@runtime_checkable
class BillChecker(Protocol):
    """
    Protocol for bill checking services.
    
    All provider-specific implementations must conform to this interface.
    This allows for:
    - Easy testing with mock implementations
    - Swapping between simulation and real scraping logic
    - Dependency injection in endpoints
    
    Example:
        class PLNBillChecker:
            async def check_bill(self, customer_id: str) -> BillCheckResponse:
                # Implementation here
                ...
    """

    async def check_bill(self, customer_id: str) -> BillCheckResponse:
        """
        Check the bill for a given customer ID.
        
        Args:
            customer_id: The customer's ID number from the utility provider.
            
        Returns:
            BillCheckResponse with bill details or error status.
            
        Raises:
            Should NOT raise exceptions - instead return BillCheckResponse
            with status=ERROR and appropriate message.
        """
        ...


class BaseBillChecker(ABC):
    """
    Abstract base class for bill checker implementations.
    
    Provides common functionality and enforces the interface.
    Subclasses must implement the `check_bill` method.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (PLN, PDAM, INDIHOME)."""
        ...

    @abstractmethod
    async def check_bill(self, customer_id: str) -> BillCheckResponse:
        """
        Check the bill for a given customer ID.
        
        Must be implemented by subclasses.
        """
        ...

    def _validate_customer_id(self, customer_id: str) -> bool:
        """
        Validate customer ID format.
        
        Override in subclasses for provider-specific validation.
        """
        return bool(customer_id and len(customer_id) >= 6)

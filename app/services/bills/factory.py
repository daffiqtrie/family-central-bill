"""Factory for creating provider-specific bill checkers.

This module provides a factory function that returns the appropriate
BillChecker implementation based on the provider type.
"""

from app.schemas.bill import ProviderEnum
from app.services.bills.base import BillChecker
from app.services.bills.indihome import IndihomeBillChecker
from app.services.bills.pdam import PDAMBillChecker
from app.services.bills.pln import PLNBillChecker

# Registry of provider implementations
_CHECKER_REGISTRY: dict[ProviderEnum, type[BillChecker]] = {
    ProviderEnum.PLN: PLNBillChecker,
    ProviderEnum.PDAM: PDAMBillChecker,
    ProviderEnum.INDIHOME: IndihomeBillChecker,
}


def get_bill_checker(provider: ProviderEnum) -> BillChecker:
    """
    Factory function to get the appropriate bill checker for a provider.
    
    Args:
        provider: The utility provider enum value.
        
    Returns:
        An instance of the appropriate BillChecker implementation.
        
    Raises:
        ValueError: If the provider is not supported.
        
    Example:
        checker = get_bill_checker(ProviderEnum.PLN)
        result = await checker.check_bill("123456789012")
    """
    checker_class = _CHECKER_REGISTRY.get(provider)
    
    if checker_class is None:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return checker_class()


def register_checker(provider: ProviderEnum, checker_class: type[BillChecker]) -> None:
    """
    Register a custom bill checker implementation.
    
    Useful for testing or adding new providers at runtime.
    
    Args:
        provider: The provider enum to register.
        checker_class: The BillChecker class to use for this provider.
    """
    _CHECKER_REGISTRY[provider] = checker_class

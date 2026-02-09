"""Bill Orchestrator Service.

This module provides the smart caching layer for bill checking.
It sits between the API endpoints and the scrapers, handling:

1. Cache-first lookups with 12-hour TTL
2. Automatic cache updates on successful scrapes
3. Fallback to stale cache when scrapers fail
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bill import BillCache
from app.schemas.bill import BillCheckResponse, BillDetail, BillPeriod, BillStatus, ProviderEnum
from app.services.bills.pln import PLNBillChecker
from app.services.bills.pdam import PDAMBillChecker
from app.services.bills.indihome import IndihomeBillChecker


# Cache TTL in hours
CACHE_TTL_HOURS = 12


class BillOrchestrator:
    """
    Smart bill checking orchestrator with caching.
    
    Flow:
    1. Check cache for recent data (< 12 hours old)
    2. If cache hit: return cached data
    3. If cache miss/stale: call scraper
    4. If scraper succeeds: update cache, return fresh data
    5. If scraper fails: return stale cache (if available) or raise error
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._checkers = {
            ProviderEnum.PLN: PLNBillChecker(),
            ProviderEnum.PDAM: PDAMBillChecker(),
            ProviderEnum.INDIHOME: IndihomeBillChecker(),
        }
    
    async def get_bill_data(
        self,
        provider: ProviderEnum,
        customer_id: str,
        force_refresh: bool = False,
    ) -> BillCheckResponse:
        """
        Get bill data with smart caching.
        
        Args:
            provider: Bill provider (PLN, PDAM, INDIHOME)
            customer_id: Customer ID number
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            BillCheckResponse with bill data
        """
        provider_str = provider.value
        
        # Step 1: Check cache (unless force refresh)
        cached_data = None
        if not force_refresh:
            cached_data = await self._get_cached_bill(provider_str, customer_id)
            
            if cached_data and self._is_cache_fresh(cached_data):
                if settings.DEBUG:
                    print(f"[CACHE] HIT - {provider_str}:{customer_id} (fresh)")
                return self._cache_to_response(cached_data)
        
        # Step 2: Call the scraper
        checker = self._checkers.get(provider)
        if not checker:
            return BillCheckResponse(
                provider=provider,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Provider {provider_str} tidak didukung",
            )
        
        try:
            if settings.DEBUG:
                print(f"[CACHE] MISS - {provider_str}:{customer_id} - calling scraper")
            
            response = await checker.check_bill(customer_id)
            
            # Step 3: Update cache on success
            if response.status in (BillStatus.UNPAID, BillStatus.PAID, BillStatus.OVERDUE):
                await self._update_cache(provider_str, customer_id, response)
                if settings.DEBUG:
                    print(f"[CACHE] UPDATED - {provider_str}:{customer_id}")
            
            return response
            
        except Exception as e:
            if settings.DEBUG:
                print(f"[CACHE] SCRAPER FAILED - {provider_str}:{customer_id}: {e}")
            
            # Step 4: Fallback to stale cache if available
            if cached_data:
                if settings.DEBUG:
                    print(f"[CACHE] FALLBACK to stale cache")
                response = self._cache_to_response(cached_data)
                response.message = f"[STALE CACHE] {response.message or 'Data dari cache'}"
                return response
            
            # No cache, return error
            return BillCheckResponse(
                provider=provider,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Gagal mengambil data: {str(e)}",
            )
    
    async def _get_cached_bill(self, provider: str, customer_id: str) -> BillCache | None:
        """Get cached bill data from database."""
        stmt = select(BillCache).where(
            BillCache.provider == provider,
            BillCache.customer_id == customer_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def _is_cache_fresh(self, cache: BillCache) -> bool:
        """Check if cache is still within TTL."""
        if not cache.updated_at:
            return False
        
        now = datetime.now(timezone.utc)
        cache_time = cache.updated_at
        
        # Handle naive datetime
        if cache_time.tzinfo is None:
            cache_time = cache_time.replace(tzinfo=timezone.utc)
        
        age = now - cache_time
        return age < timedelta(hours=CACHE_TTL_HOURS)
    
    async def _update_cache(
        self,
        provider: str,
        customer_id: str,
        response: BillCheckResponse,
    ) -> None:
        """Update or create cache entry."""
        # Build period string
        period_str = None
        if response.bills:
            periods = [f"{b.period.month}/{b.period.year}" for b in response.bills]
            period_str = ",".join(periods)
        
        # Serialize full response
        response_dict = {
            "provider": response.provider.value,
            "customer_id": response.customer_id,
            "customer_name": response.customer_name,
            "status": response.status.value,
            "total_amount": str(response.total_amount) if response.total_amount else "0",
            "message": response.message,
            "tariff_class": response.tariff_class,
            "power_rating": response.power_rating,
            "meter_number": response.meter_number,
            "bills": [
                {
                    "period": {"month": b.period.month, "year": b.period.year},
                    "amount": str(b.amount),
                    "admin_fee": str(b.admin_fee),
                }
                for b in (response.bills or [])
            ]
        }
        response_json = json.dumps(response_dict)
        
        # Check if cache entry exists
        existing = await self._get_cached_bill(provider, customer_id)
        
        if existing:
            # Update existing
            existing.customer_name = response.customer_name
            existing.status = response.status.value
            existing.amount = int(response.total_amount or 0)
            existing.period = period_str
            existing.response_json = response_json
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            cache = BillCache(
                provider=provider,
                customer_id=customer_id,
                customer_name=response.customer_name,
                status=response.status.value,
                amount=int(response.total_amount or 0),
                period=period_str,
                response_json=response_json,
            )
            self.db.add(cache)
        
        await self.db.commit()
    
    def _cache_to_response(self, cache: BillCache) -> BillCheckResponse:
        """Convert cache entry back to BillCheckResponse."""
        # Try to restore from full JSON first
        if cache.response_json:
            try:
                data = json.loads(cache.response_json)
                
                # Reconstruct bills
                bills = []
                for bill_data in data.get("bills", []):
                    period = bill_data.get("period", {})
                    bills.append(BillDetail(
                        period=BillPeriod(
                            month=period.get("month", 1),
                            year=period.get("year", 2026),
                        ),
                        amount=Decimal(bill_data.get("amount", "0")),
                        admin_fee=Decimal(bill_data.get("admin_fee", "0")),
                    ))
                
                return BillCheckResponse(
                    provider=ProviderEnum(data.get("provider", "PLN")),
                    customer_id=data.get("customer_id", cache.customer_id),
                    customer_name=data.get("customer_name", cache.customer_name),
                    status=BillStatus(data.get("status", cache.status)),
                    bills=bills,
                    total_amount=Decimal(data.get("total_amount", "0")),
                    tariff_class=data.get("tariff_class"),
                    power_rating=data.get("power_rating"),
                    meter_number=data.get("meter_number"),
                    checked_at=cache.updated_at,
                    message=data.get("message"),
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        # Fallback to basic reconstruction
        return BillCheckResponse(
            provider=ProviderEnum(cache.provider),
            customer_id=cache.customer_id,
            customer_name=cache.customer_name,
            status=BillStatus(cache.status),
            total_amount=Decimal(cache.amount) if cache.amount else None,
            checked_at=cache.updated_at,
            message="Data dari cache",
        )


async def get_bill_data(
    db: AsyncSession,
    provider: ProviderEnum,
    customer_id: str,
    force_refresh: bool = False,
) -> BillCheckResponse:
    """
    Convenience function for getting bill data with caching.
    
    Args:
        db: Database session
        provider: Bill provider
        customer_id: Customer ID
        force_refresh: Bypass cache if True
        
    Returns:
        BillCheckResponse
    """
    orchestrator = BillOrchestrator(db)
    return await orchestrator.get_bill_data(provider, customer_id, force_refresh)

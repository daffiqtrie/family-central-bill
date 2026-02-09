"""Bill checking API endpoints with smart caching."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.bill import BillCheckRequest, BillCheckResponse, ProviderEnum
from app.schemas.utility_account import UtilityAccountResponse
from app.services.bill_orchestrator import get_bill_data
from app.services.utility_account import UtilityAccountService

router = APIRouter(
    prefix="/bills",
    tags=["Bills"],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/check",
    response_model=BillCheckResponse,
    summary="Check bill for a utility account",
    responses={
        200: {"description": "Bill check successful"},
        400: {"description": "Invalid customer ID format"},
    },
)
async def check_bill(
    db: DbSession,
    request: BillCheckRequest,
    force_refresh: bool = Query(
        default=False,
        description="Bypass cache and fetch fresh data from provider"
    ),
) -> BillCheckResponse:
    """
    Check the current bill status for a utility account.
    
    Uses smart caching with 12-hour TTL to minimize API calls:
    - If cached data is less than 12 hours old, returns cached data
    - If cache is stale or missing, fetches fresh data from provider
    - If provider fails but stale cache exists, returns stale cache with warning
    
    - **provider**: The utility provider (PLN, PDAM, INDIHOME)
    - **customer_id**: Your customer number from the provider
    - **force_refresh**: Set to true to bypass cache (optional)
    
    Returns bill details including:
    - Customer name and account info
    - List of unpaid bills with periods and amounts
    - Total amount due including admin fees
    - Due date and overdue status
    """
    return await get_bill_data(
        db=db,
        provider=request.provider,
        customer_id=request.customer_id,
        force_refresh=force_refresh,
    )


@router.post(
    "/check/{account_id}",
    response_model=BillCheckResponse,
    summary="Check bill for a saved utility account",
)
async def check_saved_account_bill(
    db: DbSession,
    account_id: int,
    force_refresh: bool = Query(
        default=False,
        description="Bypass cache and fetch fresh data"
    ),
) -> BillCheckResponse:
    """
    Check the bill for a saved utility account from the database.
    
    Uses the saved customer_id and provider from the utility_accounts table.
    
    - **account_id**: The ID of the saved utility account
    - **force_refresh**: Set to true to bypass cache (optional)
    """
    service = UtilityAccountService(db)
    account = await service.get_by_id(account_id)
    
    provider = ProviderEnum(account.provider.value)
    
    return await get_bill_data(
        db=db,
        provider=provider,
        customer_id=account.customer_id,
        force_refresh=force_refresh,
    )


@router.get(
    "/saved",
    response_model=list[UtilityAccountResponse],
    summary="Get all saved utility accounts",
)
async def get_saved_accounts(
    db: DbSession,
    active_only: bool = True,
) -> list[UtilityAccountResponse]:
    """
    Retrieve all saved utility accounts from the database.
    
    - **active_only**: If true (default), only return active accounts
    """
    service = UtilityAccountService(db)
    accounts = await service.get_all()
    
    if active_only:
        accounts = [a for a in accounts if a.is_active]
    
    return [UtilityAccountResponse.model_validate(a) for a in accounts]


@router.post(
    "/check-all",
    response_model=list[BillCheckResponse],
    summary="Check bills for all saved accounts",
)
async def check_all_saved_bills(
    db: DbSession,
    active_only: bool = True,
    force_refresh: bool = Query(
        default=False,
        description="Bypass cache for all checks"
    ),
) -> list[BillCheckResponse]:
    """
    Check bills for all saved utility accounts at once.
    
    Uses smart caching - cached data will be returned for recent checks.
    
    - **active_only**: If true (default), only check active accounts
    - **force_refresh**: Set to true to bypass cache for all accounts
    """
    service = UtilityAccountService(db)
    accounts = await service.get_all()
    
    if active_only:
        accounts = [a for a in accounts if a.is_active]
    
    results: list[BillCheckResponse] = []
    
    for account in accounts:
        provider = ProviderEnum(account.provider.value)
        result = await get_bill_data(
            db=db,
            provider=provider,
            customer_id=account.customer_id,
            force_refresh=force_refresh,
        )
        results.append(result)
    
    return results

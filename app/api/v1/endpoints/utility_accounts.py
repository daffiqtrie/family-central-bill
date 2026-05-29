"""Utility accounts CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.utility_account import (
    UtilityAccountCreate,
    UtilityAccountResponse,
    UtilityAccountUpdate,
)
from app.services.utility_account import UtilityAccountService

router = APIRouter(
    prefix="/utility-accounts",
    tags=["Utility Accounts"],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_service(db: DbSession) -> UtilityAccountService:
    """Dependency to get utility account service."""
    return UtilityAccountService(db)


@router.get(
    "/",
    response_model=list[UtilityAccountResponse],
    summary="List all utility accounts",
)
async def list_utility_accounts(
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[UtilityAccountResponse]:
    """
    Retrieve all utility accounts with optional pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    service = get_service(db)
    accounts = await service.get_all(skip=skip, limit=limit)
    return [UtilityAccountResponse.model_validate(a) for a in accounts]


@router.post(
    "/",
    response_model=UtilityAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a utility account",
)
async def create_utility_account(
    db: DbSession,
    data: UtilityAccountCreate,
) -> UtilityAccountResponse:
    """
    Create a new utility account.

    - **provider**: Utility provider (PLN, PDAM, INDIHOME)
    - **customer_id**: Your customer ID from the provider
    - **alias**: Optional friendly name
    """
    service = get_service(db)
    account = await service.create(data)
    return UtilityAccountResponse.model_validate(account)


@router.get(
    "/{account_id}",
    response_model=UtilityAccountResponse,
    summary="Get a utility account",
)
async def get_utility_account(
    db: DbSession,
    account_id: int = Path(..., ge=1),
) -> UtilityAccountResponse:
    """Retrieve a specific utility account by ID."""
    service = get_service(db)
    account = await service.get_by_id(account_id)
    return UtilityAccountResponse.model_validate(account)


@router.patch(
    "/{account_id}",
    response_model=UtilityAccountResponse,
    summary="Update a utility account",
)
async def update_utility_account(
    db: DbSession,
    data: UtilityAccountUpdate,
    account_id: int = Path(..., ge=1),
) -> UtilityAccountResponse:
    """
    Update an existing utility account.

    Only provided fields will be updated (partial update).
    """
    service = get_service(db)
    account = await service.update(account_id, data)
    return UtilityAccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a utility account",
)
async def delete_utility_account(
    db: DbSession,
    account_id: int = Path(..., ge=1),
) -> None:
    """Delete a utility account by ID."""
    service = get_service(db)
    await service.delete(account_id)

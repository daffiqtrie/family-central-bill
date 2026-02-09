"""Business logic service for UtilityAccount operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.models.utility_account import UtilityAccount
from app.schemas.utility_account import UtilityAccountCreate, UtilityAccountUpdate


class UtilityAccountService:
    """Service class for managing utility accounts."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session."""
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[UtilityAccount]:
        """Get all utility accounts with pagination."""
        query = select(UtilityAccount).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, account_id: int) -> UtilityAccount:
        """Get a utility account by ID."""
        query = select(UtilityAccount).where(UtilityAccount.id == account_id)
        result = await self.db.execute(query)
        account = result.scalar_one_or_none()
        
        if account is None:
            raise NotFoundError(resource="UtilityAccount", identifier=account_id)
        
        return account

    async def get_by_customer_id(self, customer_id: str) -> UtilityAccount | None:
        """Get a utility account by customer ID."""
        query = select(UtilityAccount).where(UtilityAccount.customer_id == customer_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: UtilityAccountCreate) -> UtilityAccount:
        """Create a new utility account."""
        account = UtilityAccount(**data.model_dump())
        
        try:
            self.db.add(account)
            await self.db.flush()
            await self.db.refresh(account)
            return account
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError(
                resource="UtilityAccount",
                field="customer_id",
                value=data.customer_id,
            )

    async def update(
        self,
        account_id: int,
        data: UtilityAccountUpdate,
    ) -> UtilityAccount:
        """Update an existing utility account."""
        account = await self.get_by_id(account_id)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        
        try:
            await self.db.flush()
            await self.db.refresh(account)
            return account
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateError(
                resource="UtilityAccount",
                field="customer_id",
                value=data.customer_id,
            )

    async def delete(self, account_id: int) -> None:
        """Delete a utility account."""
        account = await self.get_by_id(account_id)
        await self.db.delete(account)
        await self.db.flush()

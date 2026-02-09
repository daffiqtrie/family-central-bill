"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import bills, utility_accounts

router = APIRouter()

# Include all endpoint routers
router.include_router(utility_accounts.router)
router.include_router(bills.router)

# Add additional routers here as the API grows:
# router.include_router(payments.router)

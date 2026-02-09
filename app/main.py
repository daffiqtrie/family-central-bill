"""FamilyCentralAPI - Home server application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exceptions import (
    FamilyCentralException,
    family_central_exception_handler,
    http_exception_handler,
)
from app.core.security import FamilyKeyAuthMiddleware
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup: Always create tables (SQLite file will be created if needed)
    await init_db()
    
    yield
    
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Home server API for managing family utilities and services",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware (order matters: first added = last executed)
# ─────────────────────────────────────────────────────────────────────────────

# CORS middleware (if needed for frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (API key validation)
app.add_middleware(FamilyKeyAuthMiddleware)

# ─────────────────────────────────────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────────────────────────────────────

app.add_exception_handler(FamilyCentralException, family_central_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint - returns API info."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
        "database": "SQLite" if settings.is_sqlite else "External",
    }


@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

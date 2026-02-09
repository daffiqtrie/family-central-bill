"""Async database session and engine configuration for SQLite."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _get_engine_kwargs() -> dict[str, Any]:
    """Get engine kwargs based on database type."""
    kwargs: dict[str, Any] = {
        "echo": settings.DEBUG,
    }
    
    if settings.is_sqlite:
        # SQLite-specific settings
        kwargs.update({
            # Required for SQLite with async - allows multi-threaded access
            "connect_args": {"check_same_thread": False},
            # Use StaticPool for SQLite to maintain single connection
            # This is recommended for SQLite with async
            "poolclass": StaticPool,
        })
    else:
        # Connection pool settings for other databases (MySQL, PostgreSQL)
        kwargs.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        })
    
    return kwargs


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs(),
)

# Session factory for creating new sessions
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in SQLAlchemy models.
    For SQLite, this also creates the database file if it doesn't exist.
    """
    # Import all models to ensure they're registered with Base
    from app.db.base_class import Base
    from app.models import UtilityAccount  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

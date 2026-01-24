"""
Database Session Management.

This module provides:
- SQLAlchemy async engine with connection pooling
- Session factory for creating database sessions
- FastAPI dependency for request-scoped sessions
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


# =============================================================================
# Async Engine Configuration
# =============================================================================

# Create async engine with connection pooling
# Using asyncpg driver for PostgreSQL async support
engine = create_async_engine(
    settings.DATABASE_URL,
    
    # Connection pool settings
    # pool_size: Number of connections to keep open
    pool_size=settings.DB_POOL_SIZE,
    
    # max_overflow: Extra connections allowed beyond pool_size
    # These are created when pool is exhausted, then closed when returned
    max_overflow=settings.DB_MAX_OVERFLOW,
    
    # Echo SQL statements to stdout (useful for debugging)
    # WARNING: Disable in production for performance
    echo=settings.DEBUG,
    
    # Recycle connections after 30 minutes to prevent stale connections
    pool_recycle=1800,
    
    # Pre-ping connections to verify they're still alive
    pool_pre_ping=True,
)

# For testing, use NullPool to avoid connection issues
# Uncomment for testing:
# test_engine = create_async_engine(
#     settings.DATABASE_URL,
#     poolclass=NullPool,
#     echo=True,
# )


# =============================================================================
# Session Factory
# =============================================================================

# Async session factory
# expire_on_commit=False prevents attributes from expiring after commit,
# which is needed for async operations where we access attributes after commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# FastAPI Dependency
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Creates a new session for each request and ensures proper cleanup.
    The session is automatically closed when the request completes,
    even if an exception occurs.
    
    Usage in FastAPI:
        @app.get("/rides")
        async def get_rides(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(RideDB))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Commit any pending changes if no exception occurred
            await session.commit()
        except Exception:
            # Rollback on any exception
            await session.rollback()
            raise
        finally:
            # Always close the session
            await session.close()


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for read-only database operations.
    
    Same as get_db() but doesn't commit, useful for GET endpoints
    where no modifications are made.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

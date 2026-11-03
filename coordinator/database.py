"""
SQLAlchemy 2.0 Async Database Connection and Session Management.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from coordinator.config import get_settings

settings = get_settings()

# Declarative Base for all models
Base = declarative_base()

# Global Async Engine
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,  # type: ignore[arg-type]
    echo=settings.DEBUG,
    future=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session with automatic transaction handling.
    Rolls back automatically on unhandled exception.
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


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for standalone async database transactions (e.g. background tasks)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict[str, float | str | bool]:
    """Execute a lightweight query to verify PostgreSQL connectivity and measure latency."""
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "healthy",
            "connected": True,
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
        }


async def close_db_connections() -> None:
    """Dispose of engine connections gracefully during application shutdown."""
    await engine.dispose()

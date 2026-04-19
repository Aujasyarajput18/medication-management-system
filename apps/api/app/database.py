"""
Aujasya — Database Configuration
[FIX-6] Exports BOTH async engine (for FastAPI) and sync engine (for Celery).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# ══════════════════════════════════════════════════════════════════════════════
# ASYNC ENGINE — Used by FastAPI request handlers
# ══════════════════════════════════════════════════════════════════════════════
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.is_development,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ══════════════════════════════════════════════════════════════════════════════
# SYNC ENGINE — Used ONLY by Celery tasks [FIX-6]
# Celery tasks are synchronous. They cannot use `await` or `AsyncSession`.
# Every Celery task uses SyncSessionLocal for DB access.
# This is a hard boundary — do not mix.
# ══════════════════════════════════════════════════════════════════════════════
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session() -> Session:
    """
    Celery dependency: returns a sync database session.
    Must be used with a context manager or manually closed.
    """
    return SyncSessionLocal()

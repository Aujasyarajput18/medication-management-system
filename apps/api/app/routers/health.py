"""
Aujasya — Health Check Router
Verifies database and Redis connectivity.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, RedisClient

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health check")
async def health_check(
    db: DbSession,
    redis: RedisClient,
) -> dict:
    """
    Check connectivity to PostgreSQL and Redis.
    Returns 200 with status of each dependency.
    """
    status_report: dict = {"status": "healthy", "services": {}}

    # Check PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        status_report["services"]["postgres"] = "connected"
    except Exception as e:
        status_report["status"] = "degraded"
        status_report["services"]["postgres"] = f"error: {type(e).__name__}"

    # Check Redis
    try:
        pong = await redis.ping()
        status_report["services"]["redis"] = "connected" if pong else "no response"
    except Exception as e:
        status_report["status"] = "degraded"
        status_report["services"]["redis"] = f"error: {type(e).__name__}"

    return status_report

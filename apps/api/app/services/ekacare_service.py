"""
Aujasya — Ekacare API Service
Medicine database lookup with circuit breaker protection.
"""

from __future__ import annotations

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()


class EkacareService:
    """HTTP client for Ekacare medicine database API."""

    def __init__(self, redis: Redis) -> None:
        self.breaker = CircuitBreaker(redis, "ekacare", failure_threshold=5, recovery_timeout_s=60)

    async def search_by_brand(self, brand_name: str) -> list[dict]:
        """Search for generic alternatives by brand name."""
        if await self.breaker.is_open():
            logger.info("ekacare_circuit_open")
            return []

        if not settings.EKACARE_API_KEY:
            logger.warning("ekacare_not_configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.EKACARE_API_URL}/v1/medicines/search",
                    params={"query": brand_name, "type": "generic"},
                    headers={"Authorization": f"Bearer {settings.EKACARE_API_KEY}"},
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                data = resp.json()
                return data.get("alternatives", [])
            else:
                await self.breaker.record_failure()
                logger.error("ekacare_search_failed", status=resp.status_code)
                return []

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("ekacare_request_failed", error=str(e))
            return []

    async def get_medicine_details(self, medicine_code: str) -> dict | None:
        """Get detailed medicine info by code."""
        if await self.breaker.is_open() or not settings.EKACARE_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.EKACARE_API_URL}/v1/medicines/{medicine_code}",
                    headers={"Authorization": f"Bearer {settings.EKACARE_API_KEY}"},
                )
            if resp.status_code == 200:
                await self.breaker.record_success()
                return resp.json()
            await self.breaker.record_failure()
            return None
        except Exception as e:
            await self.breaker.record_failure()
            logger.error("ekacare_details_failed", error=str(e))
            return None

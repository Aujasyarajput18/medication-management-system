"""
Aujasya — PMBJP / Jan Aushadhi API Service
Jan Aushadhi generic drug lookup + Kendra locator with circuit breaker.
"""

from __future__ import annotations

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()


class PmbjpService:
    """HTTP client for PMBJP Jan Aushadhi API."""

    def __init__(self, redis: Redis) -> None:
        self.breaker = CircuitBreaker(redis, "pmbjp", failure_threshold=5, recovery_timeout_s=60)

    async def search_generic(self, active_ingredient: str) -> list[dict]:
        """Search for Jan Aushadhi generics by active ingredient."""
        if await self.breaker.is_open():
            return []

        if not settings.PMBJP_API_KEY:
            logger.warning("pmbjp_not_configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.PMBJP_API_URL}/medicines/search",
                    params={"ingredient": active_ingredient},
                    headers={"X-Api-Key": settings.PMBJP_API_KEY},
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                return resp.json().get("medicines", [])
            await self.breaker.record_failure()
            return []

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("pmbjp_search_failed", error=str(e))
            return []

    async def find_nearest_kendras(
        self, lat: float, lng: float, radius_km: int | None = None
    ) -> list[dict]:
        """Find nearest Jan Aushadhi Kendras by geolocation."""
        if await self.breaker.is_open():
            return []

        radius = radius_km or settings.PMBJP_LOCATOR_RADIUS_KM

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.PMBJP_API_URL}/kendras/nearby",
                    params={"lat": lat, "lng": lng, "radius_km": radius},
                    headers={"X-Api-Key": settings.PMBJP_API_KEY} if settings.PMBJP_API_KEY else {},
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                return resp.json().get("kendras", [])
            await self.breaker.record_failure()
            return []

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("pmbjp_kendra_search_failed", error=str(e))
            return []

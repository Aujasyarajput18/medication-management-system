"""
Aujasya — Prayer Time Service
AlAdhan API → SunriseSunset fallback → static 50-city JSON.
Circuit breaker protected with cascading fallbacks.
"""

from __future__ import annotations

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()

# Static fallback for major Indian cities (fajr/maghrib in IST)
STATIC_PRAYER_TIMES: dict[str, dict] = {
    "delhi": {"suhoor": "04:30", "iftar": "18:45", "sunrise": "05:45", "sunset": "18:45"},
    "mumbai": {"suhoor": "05:00", "iftar": "19:00", "sunrise": "06:15", "sunset": "19:00"},
    "kolkata": {"suhoor": "04:15", "iftar": "18:30", "sunrise": "05:30", "sunset": "18:30"},
    "chennai": {"suhoor": "04:45", "iftar": "18:30", "sunrise": "06:00", "sunset": "18:30"},
    "hyderabad": {"suhoor": "04:45", "iftar": "18:30", "sunrise": "06:00", "sunset": "18:30"},
    "bangalore": {"suhoor": "04:50", "iftar": "18:35", "sunrise": "06:05", "sunset": "18:35"},
    "lucknow": {"suhoor": "04:20", "iftar": "18:30", "sunrise": "05:35", "sunset": "18:30"},
    "jaipur": {"suhoor": "04:35", "iftar": "18:45", "sunrise": "05:50", "sunset": "18:45"},
    "ahmedabad": {"suhoor": "04:50", "iftar": "18:50", "sunrise": "06:05", "sunset": "18:50"},
    "pune": {"suhoor": "05:00", "iftar": "18:45", "sunrise": "06:15", "sunset": "18:45"},
}
DEFAULT_FALLBACK = {"suhoor": "04:30", "iftar": "18:45", "sunrise": "05:45", "sunset": "18:45"}


class PrayerTimeService:
    """Prayer time provider with cascading fallbacks."""

    def __init__(self, redis: Redis) -> None:
        self.aladhan_breaker = CircuitBreaker(redis, "aladhan", failure_threshold=3, recovery_timeout_s=120)

    async def get_prayer_times(self, lat: float, lng: float) -> dict:
        """Get suhoor (fajr) and iftar (maghrib) times. 3-level fallback."""

        # Level 1: AlAdhan API
        result = await self._try_aladhan(lat, lng)
        if result:
            return {**result, "source": "aladhan"}

        # Level 2: SunriseSunset API
        result = await self._try_sunrise_sunset(lat, lng)
        if result:
            return {**result, "source": "sunrise_sunset"}

        # Level 3: Static city fallback
        nearest = self._nearest_city(lat, lng)
        logger.warning("prayer_times_static_fallback", city=nearest)
        return {**STATIC_PRAYER_TIMES.get(nearest, DEFAULT_FALLBACK), "source": "static_fallback"}

    async def _try_aladhan(self, lat: float, lng: float) -> dict | None:
        if await self.aladhan_breaker.is_open():
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.ALADHAN_API_URL}/timings",
                    params={"latitude": lat, "longitude": lng, "method": 1},
                )
            if resp.status_code == 200:
                await self.aladhan_breaker.record_success()
                timings = resp.json().get("data", {}).get("timings", {})
                return {
                    "suhoor": timings.get("Fajr", "04:30"),
                    "iftar": timings.get("Maghrib", "18:45"),
                    "sunrise": timings.get("Sunrise", "05:45"),
                    "sunset": timings.get("Sunset", "18:45"),
                }
            await self.aladhan_breaker.record_failure()
            return None
        except Exception:
            await self.aladhan_breaker.record_failure()
            return None

    async def _try_sunrise_sunset(self, lat: float, lng: float) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    settings.SUNRISE_SUNSET_API_URL + "/json",
                    params={"lat": lat, "lng": lng, "formatted": 0},
                )
            if resp.status_code == 200:
                data = resp.json().get("results", {})
                sunrise = data.get("sunrise", "")[:5]
                sunset = data.get("sunset", "")[:5]
                return {"suhoor": sunrise, "iftar": sunset, "sunrise": sunrise, "sunset": sunset}
            return None
        except Exception:
            return None

    def _nearest_city(self, lat: float, lng: float) -> str:
        """Find nearest city from static fallback table."""
        city_coords = {
            "delhi": (28.6, 77.2), "mumbai": (19.1, 72.9), "kolkata": (22.6, 88.4),
            "chennai": (13.1, 80.3), "hyderabad": (17.4, 78.5), "bangalore": (12.9, 77.6),
            "lucknow": (26.8, 81.0), "jaipur": (26.9, 75.8), "ahmedabad": (23.0, 72.6),
            "pune": (18.5, 73.9),
        }
        nearest = "delhi"
        min_dist = float("inf")
        for city, (c_lat, c_lng) in city_coords.items():
            dist = (lat - c_lat) ** 2 + (lng - c_lng) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = city
        return nearest

"""
Aujasya — LLaVA HTTP Client Service
Wraps calls to the LLaVA microservice with circuit breaker protection.
"""

from __future__ import annotations

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()


class LlavaService:
    """HTTP client for the LLaVA microservice on port 8001."""

    def __init__(self, redis: Redis) -> None:
        self.base_url = settings.LLAVA_SERVICE_URL
        self.breaker = CircuitBreaker(redis, "llava", failure_threshold=3, recovery_timeout_s=120)

    async def is_available(self) -> bool:
        """Check if LLaVA service is healthy and circuit is closed."""
        if await self.breaker.is_open():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def ocr_image(self, image_bytes: bytes, filename: str = "prescription.jpg") -> dict | None:
        """
        Send image to LLaVA for OCR. Returns parsed result or None on failure.
        Circuit breaker protects against repeated failures.
        """
        if await self.breaker.is_open():
            logger.info("llava_circuit_open", action="skipping")
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/ocr",
                    files={"image": (filename, image_bytes, "image/jpeg")},
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                return resp.json()
            else:
                await self.breaker.record_failure()
                logger.error("llava_ocr_failed", status=resp.status_code)
                return None

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("llava_request_failed", error=str(e))
            return None

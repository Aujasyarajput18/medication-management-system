"""
Aujasya — Rate Limit Middleware
[FIX-13] Registered LAST → runs FIRST (outermost).
Redis sliding window rate limiting per IP and per user.
"""

from __future__ import annotations

import time

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = structlog.get_logger()

# Rate limit configurations per endpoint pattern
RATE_LIMITS: dict[str, dict[str, int]] = {
    # pattern: {"max_requests": N, "window_seconds": T}
    "/auth/send-otp": {"max_requests": 5, "window_seconds": 3600},
    "/auth/verify-otp": {"max_requests": 10, "window_seconds": 900},
    "/doses": {"max_requests": 300, "window_seconds": 60},
    "/medicines": {"max_requests": 100, "window_seconds": 60},
}

# Default: 300 requests per minute
DEFAULT_LIMIT = {"max_requests": 300, "window_seconds": 60}

# Endpoints that skip rate limiting entirely
SKIP_PATHS = {"/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based sliding window rate limiter.
    [FIX-13] This middleware runs FIRST (outermost).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip rate limiting for health checks and docs
        if path in SKIP_PATHS:
            return await call_next(request)

        # Get client identifier (IP or user ID if available)
        client_id = self._get_client_id(request)
        if not client_id:
            return await call_next(request)

        # Find matching rate limit config
        limit_config = self._get_limit_config(path)

        # Check rate limit using Redis sliding window
        try:
            redis = request.app.state.redis
            is_allowed, remaining, retry_after = await self._check_rate_limit(
                redis, client_id, path, limit_config
            )

            if not is_allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    client=client_id,
                    path=path,
                    retry_after=retry_after,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "Too many requests. Please try again later.",
                        "data": None,
                        "errors": None,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        except Exception as e:
            # If Redis is down, allow the request (fail open for availability)
            logger.error("rate_limit_redis_error", error=str(e))
            return await call_next(request)

    def _get_client_id(self, request: Request) -> str | None:
        """Extract client identifier for rate limiting."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return None

    def _get_limit_config(self, path: str) -> dict[str, int]:
        """Find the rate limit config for a given path."""
        for pattern, config in RATE_LIMITS.items():
            if pattern in path:
                return config
        return DEFAULT_LIMIT

    async def _check_rate_limit(
        self,
        redis,
        client_id: str,
        path: str,
        config: dict[str, int],
    ) -> tuple[bool, int, int]:
        """
        Sliding window rate limit check using Redis sorted sets.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        max_requests = config["max_requests"]
        window = config["window_seconds"]

        # Build a path-category key to avoid cross-endpoint interference
        path_category = "default"
        for pattern in RATE_LIMITS:
            if pattern in path:
                path_category = pattern.replace("/", "_").strip("_")
                break

        key = f"rl:{path_category}:{client_id}"
        now = time.time()
        window_start = now - window

        pipe = redis.pipeline()
        # Remove entries outside the window
        await pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        await pipe.zadd(key, {f"{now}": now})
        # Count entries in window
        await pipe.zcard(key)
        # Set TTL on the key
        await pipe.expire(key, window)
        results = await pipe.execute()

        current_count = results[2]
        remaining = max(0, max_requests - current_count)
        is_allowed = current_count <= max_requests
        retry_after = window if not is_allowed else 0

        return is_allowed, remaining, retry_after

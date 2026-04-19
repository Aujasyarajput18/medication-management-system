"""
Aujasya — Auth Middleware
[FIX-13] Registered THIRD → runs SECOND.
[FIX-20] Checks jti blacklist in Redis.
Validates JWT on protected routes, establishes user identity.
"""

from __future__ import annotations

import jwt
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.config import settings

logger = structlog.get_logger()

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/send-otp",
    "/api/v1/auth/verify-otp",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT validation middleware.
    [FIX-13] Runs SECOND — after rate limiting, before RBAC.
    Sets request.state.user_id, request.state.user_role, request.state.jti.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # Also skip for refresh endpoint (uses cookie, not bearer)
        if path == "/api/v1/auth/refresh":
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Missing or invalid authorization header",
                    "data": None,
                    "errors": None,
                },
            )

        token = auth_header[7:]

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Access token has expired",
                    "data": None,
                    "errors": None,
                },
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Invalid access token",
                    "data": None,
                    "errors": None,
                },
            )

        # [FIX-20] Check jti blacklist in Redis
        jti = payload.get("jti")
        if jti:
            try:
                redis = request.app.state.redis
                is_blacklisted = await redis.exists(f"jti_blacklist:{jti}")
                if is_blacklisted:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "success": False,
                            "message": "Token has been revoked",
                            "data": None,
                            "errors": None,
                        },
                    )
            except Exception as e:
                logger.error("jti_blacklist_check_failed", error=str(e))
                # Fail open — if Redis is down, allow the request

        # Set user info on request state for downstream use
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        request.state.jti = jti

        return await call_next(request)

"""
Aujasya — RBAC Middleware
[FIX-13] Registered SECOND → runs THIRD.
Checks user role has permission for the requested endpoint.
Requires user identity from auth middleware (step 2).
"""

from __future__ import annotations

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = structlog.get_logger()

# Permission matrix: role → allowed path patterns → allowed methods
PERMISSION_MATRIX: dict[str, dict[str, set[str]]] = {
    "patient": {
        "/api/v1/medicines": {"GET", "POST", "PATCH", "DELETE"},
        "/api/v1/doses": {"GET", "POST", "PATCH"},
        "/api/v1/caregivers": {"GET", "POST", "DELETE"},
        "/api/v1/notifications": {"GET", "POST", "PATCH"},
        "/api/v1/auth": {"GET", "POST"},
    },
    "caregiver": {
        "/api/v1/medicines": {"GET"},          # Read-only for linked patients
        "/api/v1/doses": {"GET", "PATCH"},     # Can view and update dose status
        "/api/v1/caregivers": {"GET", "POST"}, # Can view/accept links
        "/api/v1/notifications": {"GET", "POST", "PATCH"},
        "/api/v1/auth": {"GET", "POST"},
    },
}

# Paths that skip RBAC (public or self-governed)
SKIP_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/send-otp",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/api/v1/auth/logout",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
}


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Role-Based Access Control middleware.
    [FIX-13] Runs THIRD — after auth establishes user identity.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip for non-API, public, and auth paths
        if not path.startswith("/api/") or path in SKIP_PATHS:
            return await call_next(request)

        # User identity must exist (set by auth middleware)
        user_role = getattr(request.state, "user_role", None)
        if not user_role:
            # No user identity — let the endpoint-level dependency handle it
            return await call_next(request)

        method = request.method

        # Check permissions
        role_permissions = PERMISSION_MATRIX.get(user_role, {})
        is_allowed = False

        for allowed_path, allowed_methods in role_permissions.items():
            if path.startswith(allowed_path) and method in allowed_methods:
                is_allowed = True
                break

        if not is_allowed:
            logger.warning(
                "rbac_denied",
                user_role=user_role,
                path=path,
                method=method,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": f"Insufficient permissions. Role '{user_role}' cannot {method} {path}",
                    "data": None,
                    "errors": None,
                },
            )

        return await call_next(request)

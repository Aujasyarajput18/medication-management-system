"""
Aujasya — FastAPI Application Entry Point
[FIX-13] Middleware registration order is explicitly defined.

FastAPI processes middleware in REVERSE registration order (LIFO stack).
We want execution order: rate_limit → auth → RBAC → audit
So we REGISTER in reverse: audit first, RBAC second, auth third, rate_limit last.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings

logger = structlog.get_logger()

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    # Startup
    logger.info("starting_aujasya", env=settings.APP_ENV)

    # Initialize Redis client
    app.state.redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    # Verify Redis connectivity
    try:
        await app.state.redis.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))

    # Initialize Sentry if configured
    if settings.SENTRY_DSN and not settings.is_testing:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        )
        logger.info("sentry_initialized")

    yield

    # Shutdown
    await app.state.redis.close()
    logger.info("aujasya_shutdown")


app = FastAPI(
    title="Aujasya API",
    description="Medication Adherence Platform for Indian Adults",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs" if settings.is_development else None,
    redoc_url=f"{API_PREFIX}/redoc" if settings.is_development else None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# NEVER use wildcard origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept-Language"],
)

# ══════════════════════════════════════════════════════════════════════════════
# [FIX-13] MIDDLEWARE REGISTRATION ORDER — READ CAREFULLY BEFORE MODIFYING
#
# FastAPI uses ASGI middleware stacking (LIFO). The LAST middleware registered
# wraps the outermost layer and processes the incoming request FIRST.
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │  REQUEST FLOW (top to bottom):                                      │
# │                                                                     │
# │  Client Request                                                     │
# │    ↓                                                                │
# │  1. RateLimitMiddleware  (registered LAST  → executes FIRST)        │
# │    ↓                                                                │
# │  2. AuthMiddleware       (validates JWT, sets request.state.user)    │
# │    ↓                                                                │
# │  3. RBACMiddleware       (checks permissions using user from step 2)│
# │    ↓                                                                │
# │  4. AuditMiddleware      (registered FIRST → executes LAST)         │
# │    ↓                                                                │
# │  Route Handler                                                      │
# │    ↓                                                                │
# │  4. AuditMiddleware      (logs response — has full context)          │
# │    ↓                                                                │
# │  3→2→1                   (response bubbles back up)                 │
# │    ↓                                                                │
# │  Client Response                                                    │
# └─────────────────────────────────────────────────────────────────────┘
#
# ⚠️  ADDING NEW MIDDLEWARE:
#   - To execute AFTER RateLimit but BEFORE Auth → register it between
#     AuthMiddleware and RateLimitMiddleware lines below.
#   - To execute AFTER Audit (innermost) → register it BEFORE AuditMiddleware.
#   - NEVER add middleware after RateLimitMiddleware unless it must execute
#     before rate limiting (e.g., IP extraction from proxy headers).
# ══════════════════════════════════════════════════════════════════════════════

from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.rbac_middleware import RBACMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

# REGISTRATION ORDER: first registered = innermost (executes last on request)
app.add_middleware(AuditMiddleware)         # Innermost  — executes 4th on request, 1st on response
app.add_middleware(RBACMiddleware)          #            — executes 3rd on request
app.add_middleware(AuthMiddleware)          #            — executes 2nd on request
app.add_middleware(RateLimitMiddleware)     # Outermost  — executes 1st on request, 4th on response

# ── Routers ──────────────────────────────────────────────────────────────────
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.medicines import router as medicines_router
from app.routers.doses import router as doses_router
from app.routers.caregivers import router as caregivers_router
from app.routers.notifications import router as notifications_router

# Phase 2 Routers
from app.routers.ocr import router as ocr_router
from app.routers.pill_id import router as pill_id_router
from app.routers.generics import router as generics_router
from app.routers.voice import router as voice_router
from app.routers.fasting import router as fasting_router
from app.routers.interactions import router as interactions_router
from app.routers.journal import router as journal_router

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(medicines_router, prefix=API_PREFIX)
app.include_router(doses_router, prefix=API_PREFIX)
app.include_router(caregivers_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)

# Include Phase 2 Routers
app.include_router(ocr_router, prefix=API_PREFIX)
app.include_router(pill_id_router, prefix=API_PREFIX)
app.include_router(generics_router, prefix=API_PREFIX)
app.include_router(voice_router, prefix=API_PREFIX)
app.include_router(fasting_router, prefix=API_PREFIX)
app.include_router(interactions_router, prefix=API_PREFIX)
app.include_router(journal_router, prefix=API_PREFIX)

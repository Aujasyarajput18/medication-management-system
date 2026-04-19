"""
Aujasya — FastAPI Dependencies
[FIX-19] All query functions use load_only() to avoid loading encrypted BYTEA fields.
[FIX-20] get_current_user checks jti blacklist in Redis.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_async_session
from app.models.user import User

logger = structlog.get_logger()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_async_session():
        yield session


async def get_redis(request: Request) -> Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Extract and validate the JWT from the Authorization header.
    [FIX-20] Also checks if the token's jti is blacklisted in Redis.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header[7:]

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    # [FIX-20] Check jti blacklist
    jti = payload.get("jti")
    if jti:
        is_blacklisted = await redis.exists(f"jti_blacklist:{jti}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user (without encrypted fields for performance)
    from sqlalchemy import select
    from sqlalchemy.orm import load_only

    stmt = select(User).options(
        load_only(
            User.id,
            User.phone_number,
            User.phone_verified,
            User.preferred_language,
            User.role,
            User.timezone,
            User.is_active,
        )
    ).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Attach jti to request state for logout
    request.state.jti = jti

    return user


def require_role(*roles: str):
    """Factory: dependency that checks user has one of the specified roles."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires role: {', '.join(roles)}",
            )
        return user
    return _check


# Type aliases for common dependencies
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[User, Depends(get_current_user)]
PatientUser = Annotated[User, Depends(require_role("patient"))]
CaregiverUser = Annotated[User, Depends(require_role("caregiver"))]
AnyUser = Annotated[User, Depends(require_role("patient", "caregiver"))]

"""
Aujasya — Auth Router
Endpoints: send-otp, verify-otp, refresh, logout, me
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession, RedisClient, get_current_user
from app.schemas.auth import (
    AuthResponse,
    LogoutRequest,
    OtpSessionResponse,
    RefreshRequest,
    SendOtpRequest,
    TokenResponse,
    UserResponse,
    VerifyOtpRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from X-Forwarded-For or direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post(
    "/send-otp",
    response_model=OtpSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Send OTP to phone number",
)
async def send_otp(
    body: SendOtpRequest,
    request: Request,
    db: DbSession,
    redis: RedisClient,
) -> OtpSessionResponse:
    """Generate and send a 6-digit OTP to the provided Indian mobile number."""
    try:
        service = AuthService(db, redis)
        return await service.send_otp(
            phone=body.phone,
            purpose=body.purpose,
            ip_address=_get_client_ip(request),
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/verify-otp",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and get tokens",
)
async def verify_otp(
    body: VerifyOtpRequest,
    db: DbSession,
    redis: RedisClient,
) -> AuthResponse:
    """Verify the OTP and issue JWT + refresh token pair."""
    try:
        service = AuthService(db, redis)
        return await service.verify_otp(
            session_id=body.session_id,
            otp=body.otp,
            device_info=body.device_info,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshRequest,
    db: DbSession,
    redis: RedisClient,
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair (rotation)."""
    try:
        service = AuthService(db, redis)
        return await service.refresh_tokens(raw_refresh_token=body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (revoke tokens)",
)
async def logout(
    body: LogoutRequest,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    redis: RedisClient,
) -> None:
    """
    Revoke refresh token and blacklist access token jti.
    [FIX-20] Access token jti is added to Redis blacklist for 15 minutes.
    """
    jti = getattr(request.state, "jti", None)
    service = AuthService(db, redis)
    await service.logout(
        user_id=user.id,
        raw_refresh_token=body.refresh_token,
        jti=jti or "",
        logout_all=body.logout_all,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    from app.services.encryption_service import encryption_service

    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        phone_verified=user.phone_verified,
        full_name=encryption_service.decrypt_bytes(
            getattr(user, "full_name", None), "full_name"
        ),
        date_of_birth=encryption_service.decrypt_bytes(
            getattr(user, "date_of_birth", None), "date_of_birth"
        ),
        preferred_language=user.preferred_language,
        role=user.role,
        timezone=user.timezone,
        is_active=user.is_active,
        last_seen_at=getattr(user, "last_seen_at", None),
        created_at=user.created_at,
    )

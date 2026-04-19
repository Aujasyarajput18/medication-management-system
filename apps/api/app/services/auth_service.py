"""
Aujasya — Authentication Service
[FIX-7] Uses PyJWT (not python-jose — abandoned, CVEs).
[FIX-20] Implements jti Redis blacklisting on logout (15-min TTL).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta

import jwt
import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import OtpSession, RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    OtpSessionResponse,
    TokenResponse,
    UserResponse,
)
from app.services.encryption_service import encryption_service
from app.utils.otp import generate_otp, generate_refresh_token, hash_otp, verify_otp
from app.utils.timezone import IST, now_ist
from app.utils.validators import sanitize_phone_for_logging, validate_indian_phone

logger = structlog.get_logger()


class AuthService:
    """Handles OTP authentication, JWT management, and token lifecycle."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def send_otp(
        self, phone: str, purpose: str, ip_address: str | None = None
    ) -> OtpSessionResponse:
        """
        Generate and send OTP to the given phone number.
        
        Rate limits: max 5 OTP requests per phone per hour (Redis counter).
        """
        if not validate_indian_phone(phone):
            raise ValueError("Invalid Indian phone number")

        # Check rate limit
        rate_key = f"otp_rate:{phone}"
        current_count = await self.redis.get(rate_key)
        if current_count is not None and int(current_count) >= 5:
            raise PermissionError("Too many OTP requests. Try again later.")

        # Increment rate counter
        pipe = self.redis.pipeline()
        await pipe.incr(rate_key)
        await pipe.expire(rate_key, 3600)  # 1 hour TTL
        await pipe.execute()

        # Also check IP-based rate limit
        if ip_address:
            ip_key = f"otp_rate_ip:{ip_address}"
            ip_count = await self.redis.get(ip_key)
            if ip_count is not None and int(ip_count) >= 10:
                raise PermissionError("Too many requests from this IP. Try again later.")
            pipe = self.redis.pipeline()
            await pipe.incr(ip_key)
            await pipe.expire(ip_key, 3600)
            await pipe.execute()

        # Generate OTP
        otp_plain = generate_otp()
        otp_hashed = hash_otp(otp_plain)

        # Create OTP session
        otp_session = OtpSession(
            phone_number=phone,
            otp_hash=otp_hashed,
            purpose=purpose,
            expires_at=now_ist() + timedelta(minutes=10),
            ip_address=ip_address,
        )
        self.db.add(otp_session)
        await self.db.flush()

        # Send OTP via SMS (Msg91)
        await self._send_otp_sms(phone, otp_plain)

        logger.info(
            "otp_sent",
            phone=sanitize_phone_for_logging(phone),
            purpose=purpose,
            session_id=str(otp_session.id),
        )

        return OtpSessionResponse(
            session_id=otp_session.id,
            expires_in=600,
        )

    async def verify_otp(
        self,
        session_id: uuid.UUID,
        otp: str,
        device_info: dict | None = None,
    ) -> AuthResponse:
        """
        Verify OTP and issue JWT + refresh token pair.
        Max 5 attempts per session.
        """
        # Find session
        stmt = select(OtpSession).where(
            OtpSession.id == session_id,
            OtpSession.used == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session is None:
            raise ValueError("Invalid or expired OTP session")

        # Check expiry
        if now_ist() > session.expires_at:
            raise ValueError("OTP has expired. Please request a new one.")

        # Check attempts
        if session.attempts >= 5:
            raise PermissionError("Too many failed attempts. Request a new OTP.")

        # Increment attempts
        session.attempts += 1

        # Verify OTP (bcrypt constant-time comparison)
        if not verify_otp(otp, session.otp_hash):
            await self.db.flush()
            remaining = 5 - session.attempts
            raise ValueError(f"Incorrect OTP. {remaining} attempts remaining.")

        # Mark session as used
        session.used = True
        await self.db.flush()

        # Upsert user
        user, is_new = await self._upsert_user(session.phone_number)

        # Generate tokens
        access_token = self._create_access_token(user)
        raw_refresh_token = generate_refresh_token()

        # Store hashed refresh token
        token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now_ist() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            device_info=device_info,
        )
        self.db.add(refresh_record)
        await self.db.flush()

        logger.info(
            "user_authenticated",
            user_id=str(user.id),
            phone=sanitize_phone_for_logging(session.phone_number),
            is_new_user=is_new,
        )

        # Build user response (decrypt fields)
        user_response = self._build_user_response(user)

        return AuthResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            user=user_response,
            is_new_user=is_new,
        )

    async def refresh_tokens(self, raw_refresh_token: str) -> TokenResponse:
        """
        Refresh token rotation: validate refresh token, revoke old, issue new pair.
        """
        token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        refresh_record = result.scalar_one_or_none()

        if refresh_record is None:
            raise ValueError("Invalid refresh token")

        if now_ist() > refresh_record.expires_at:
            refresh_record.revoked = True
            await self.db.flush()
            raise ValueError("Refresh token expired")

        # Revoke the old refresh token (rotation)
        refresh_record.revoked = True

        # Get user
        user_stmt = select(User).where(User.id == refresh_record.user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise ValueError("User not found or inactive")

        # Issue new tokens
        access_token = self._create_access_token(user)
        new_raw_refresh = generate_refresh_token()
        new_hash = hashlib.sha256(new_raw_refresh.encode()).hexdigest()

        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=now_ist() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            device_info=refresh_record.device_info,
        )
        self.db.add(new_refresh)
        await self.db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(
        self,
        user_id: uuid.UUID,
        raw_refresh_token: str,
        jti: str,
        logout_all: bool = False,
    ) -> None:
        """
        Logout: revoke refresh token(s) and blacklist access token jti.
        [FIX-20] Blacklists the access token's jti in Redis for 15 minutes.
        """
        # Revoke the specific refresh token
        token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        token_record = result.scalar_one_or_none()
        if token_record:
            token_record.revoked = True

        if logout_all:
            # Revoke all refresh tokens for this user
            all_stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
            )
            all_result = await self.db.execute(all_stmt)
            for record in all_result.scalars():
                record.revoked = True

        # [FIX-20] Blacklist the access token's jti in Redis
        # 15-minute TTL = access token max lifetime
        if jti:
            await self.redis.set(
                f"jti_blacklist:{jti}",
                "1",
                ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

        await self.db.flush()

        logger.info(
            "user_logged_out",
            user_id=str(user_id),
            logout_all=logout_all,
            jti_blacklisted=bool(jti),
        )

    def _create_access_token(self, user: User) -> str:
        """
        Create a JWT access token.
        [FIX-7] Uses PyJWT.
        Claims: sub, role, phone_last4, iat, exp, jti.
        """
        now = now_ist()
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(user.id),
            "role": user.role,
            "phone_last4": user.phone_number[-4:],
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": jti,
        }

        return jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    async def _upsert_user(self, phone: str) -> tuple[User, bool]:
        """Find or create user by phone number."""
        stmt = select(User).where(User.phone_number == phone)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is not None:
            user.phone_verified = True
            user.last_seen_at = now_ist()
            await self.db.flush()
            return user, False

        # Create new user
        new_user = User(
            phone_number=phone,
            phone_verified=True,
            last_seen_at=now_ist(),
        )
        self.db.add(new_user)
        await self.db.flush()
        return new_user, True

    def _build_user_response(self, user: User) -> UserResponse:
        """Build user response with decrypted fields."""
        return UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            phone_verified=user.phone_verified,
            full_name=encryption_service.decrypt_bytes(user.full_name, "full_name"),
            date_of_birth=encryption_service.decrypt_bytes(user.date_of_birth, "date_of_birth"),
            preferred_language=user.preferred_language,
            role=user.role,
            timezone=user.timezone,
            is_active=user.is_active,
            last_seen_at=user.last_seen_at,
            created_at=user.created_at,
        )

    async def _send_otp_sms(self, phone: str, otp: str) -> None:
        """
        Send OTP via Msg91 SMS.
        Gracefully degrades in development (logs to console).
        NEVER logs the actual OTP in production.
        """
        if settings.is_development or settings.is_testing:
            # Development mode — log OTP for testing (never in production)
            logger.warning(
                "dev_otp_generated",
                phone=sanitize_phone_for_logging(phone),
                otp=otp,  # Only logged in dev mode
                note="THIS MUST NEVER APPEAR IN PRODUCTION LOGS",
            )
            return

        if not settings.MSG91_API_KEY:
            logger.warning("msg91_not_configured", phone=sanitize_phone_for_logging(phone))
            return

        # Production: send via Msg91 API
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.msg91.com/api/v5/otp",
                    headers={"authkey": settings.MSG91_API_KEY},
                    json={
                        "template_id": settings.MSG91_TEMPLATE_ID_OTP,
                        "mobile": phone.replace("+", ""),
                        "otp": otp,
                    },
                    timeout=10.0,
                )
                if response.status_code != 200:
                    logger.error(
                        "msg91_send_failed",
                        status=response.status_code,
                        phone=sanitize_phone_for_logging(phone),
                    )
        except httpx.HTTPError as e:
            logger.error(
                "msg91_connection_error",
                error=str(e),
                phone=sanitize_phone_for_logging(phone),
            )

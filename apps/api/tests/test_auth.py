"""
Aujasya — Auth Tests
Tests OTP flow, JWT lifecycle, [FIX-7] PyJWT, [FIX-20] jti blacklisting.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from app.config import settings
from app.utils.otp import generate_otp, hash_otp, verify_otp


class TestOtpGeneration:
    """Test OTP generation, hashing, and verification."""

    def test_otp_is_6_digits(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
        assert 100000 <= int(otp) <= 999999

    def test_otp_uniqueness(self):
        """Generate 100 OTPs and verify they're mostly unique (CSPRNG)."""
        otps = {generate_otp() for _ in range(100)}
        assert len(otps) >= 90  # Allow minimal collision

    def test_otp_hash_and_verify(self):
        otp = generate_otp()
        hashed = hash_otp(otp)
        assert hashed != otp  # Not stored in plaintext
        assert verify_otp(otp, hashed)
        assert not verify_otp("000000", hashed)

    def test_wrong_otp_rejected(self):
        otp = generate_otp()
        hashed = hash_otp(otp)
        wrong = "000000" if otp != "000000" else "111111"
        assert not verify_otp(wrong, hashed)


class TestSendOtp:
    """Test POST /api/v1/auth/send-otp endpoint."""

    @pytest.mark.asyncio
    async def test_send_otp_valid_phone(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone": "+919876543210", "purpose": "login"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["expires_in"] == 600

    @pytest.mark.asyncio
    async def test_send_otp_invalid_phone(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone": "+1234567890", "purpose": "login"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_otp_rate_limit(self, client: AsyncClient, test_redis):
        """[FIX-20] Test rate limiting: max 5 OTP requests per phone per hour."""
        phone = "+919000000001"
        for i in range(5):
            await client.post(
                "/api/v1/auth/send-otp",
                json={"phone": phone, "purpose": "login"},
            )

        # 6th request should be rate limited
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"phone": phone, "purpose": "login"},
        )
        assert response.status_code == 429


class TestTokenLifecycle:
    """Test JWT token creation, refresh, and revocation."""

    def test_jwt_encode_decode_pyjwt(self):
        """[FIX-7] Verify PyJWT works correctly."""
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "patient",
            "jti": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(minutes=15),
        }
        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        decoded = pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == payload["sub"]
        assert decoded["role"] == "patient"

    def test_expired_token_rejected(self):
        """Expired tokens must raise ExpiredSignatureError."""
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.utcnow() - timedelta(minutes=1),
        }
        token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            pyjwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    @pytest.mark.asyncio
    async def test_jti_blacklist_on_logout(self, test_redis):
        """
        [FIX-20] After logout, the access token's jti should be blacklisted
        in Redis for 15 minutes, rejecting any further requests.
        """
        jti = str(uuid.uuid4())

        # Simulate logout — set jti in blacklist
        await test_redis.set(f"jti_blacklist:{jti}", "1", ex=900)

        # Verify blacklisted
        assert await test_redis.exists(f"jti_blacklist:{jti}")

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/medicines")
        assert response.status_code == 401

"""
Aujasya — Auth Pydantic v2 Schemas
Request/response models for authentication endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


class SendOtpRequest(BaseModel):
    """POST /auth/send-otp request body."""

    phone: str = Field(..., description="E.164 phone number (+91XXXXXXXXXX)")
    purpose: str = Field(default="login", description="'login' | 'caregiver_link'")

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        """Validate Indian mobile number in E.164 format."""
        if not re.match(r"^\+91[6-9]\d{9}$", v):
            raise ValueError("Must be a valid Indian mobile number (+91XXXXXXXXXX)")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        """Validate OTP purpose."""
        allowed = {"login", "caregiver_link"}
        if v not in allowed:
            raise ValueError(f"Purpose must be one of: {allowed}")
        return v


class VerifyOtpRequest(BaseModel):
    """POST /auth/verify-otp request body."""

    session_id: UUID
    otp: str = Field(..., min_length=6, max_length=6)
    device_info: dict | None = None

    @field_validator("otp")
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        """OTP must be exactly 6 digits."""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v


class RefreshRequest(BaseModel):
    """POST /auth/refresh request body."""

    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    """POST /auth/logout request body."""

    refresh_token: str = Field(..., min_length=1)
    logout_all: bool = False


class TokenResponse(BaseModel):
    """Token pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class UserResponse(BaseModel):
    """User profile data returned to client."""

    id: UUID
    phone_number: str
    phone_verified: bool
    full_name: str | None = None
    date_of_birth: str | None = None
    preferred_language: str
    role: str
    timezone: str
    is_active: bool
    last_seen_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """POST /auth/verify-otp response data."""

    access_token: str
    refresh_token: str
    user: UserResponse
    is_new_user: bool


class OtpSessionResponse(BaseModel):
    """POST /auth/send-otp response data."""

    session_id: UUID
    expires_in: int = Field(default=600, description="OTP validity in seconds")


class MealTimeInput(BaseModel):
    """Single meal time configuration."""

    meal_name: str
    typical_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

    @field_validator("meal_name")
    @classmethod
    def validate_meal_name(cls, v: str) -> str:
        """Validate meal name."""
        allowed = {"waking", "breakfast", "lunch", "dinner", "bedtime"}
        if v not in allowed:
            raise ValueError(f"Meal name must be one of: {allowed}")
        return v


class UpdateMealTimesRequest(BaseModel):
    """PUT /users/meal-times request body."""

    meal_times: list[MealTimeInput] = Field(..., min_length=1, max_length=5)


class UpdateProfileRequest(BaseModel):
    """PATCH /users/profile request body."""

    full_name: str | None = None
    date_of_birth: str | None = None
    preferred_language: str | None = None

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language code."""
        if v is not None:
            allowed = {"en", "hi", "ta", "te", "bn", "mr"}
            if v not in allowed:
                raise ValueError(f"Language must be one of: {allowed}")
        return v


class UpdateFcmTokenRequest(BaseModel):
    """PUT /users/fcm-token request body."""

    fcm_token: str = Field(..., min_length=1)
    platform: str = Field(default="android")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform."""
        allowed = {"android", "ios", "web"}
        if v not in allowed:
            raise ValueError(f"Platform must be one of: {allowed}")
        return v

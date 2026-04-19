"""
Aujasya — Notification Pydantic v2 Schemas
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PushSubscribeRequest(BaseModel):
    """POST /notifications/push-subscribe request body."""

    fcm_token: str = Field(..., min_length=1)
    platform: str = "android"

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"android", "ios", "web"}
        if v not in allowed:
            raise ValueError(f"Platform must be one of: {allowed}")
        return v


class NotificationPreferencesResponse(BaseModel):
    """GET /notifications/preferences response."""

    enable_push: bool = True
    enable_whatsapp: bool = False
    enable_sms: bool = False
    enable_ivr: bool = False
    escalation_delay_minutes: int = 30


class NotificationPreferencesUpdate(BaseModel):
    """PATCH /notifications/preferences request body."""

    enable_whatsapp: bool | None = None
    enable_sms: bool | None = None
    enable_ivr: bool | None = None
    escalation_delay_minutes: int | None = Field(default=None, ge=10, le=120)

"""Aujasya — Fasting Mode Pydantic Schemas"""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field, model_validator


class PrayerTimesResponse(BaseModel):
    """Response from /fasting/prayer-times."""
    suhoor: str   # HH:MM format — fajr time
    iftar: str    # HH:MM format — maghrib time
    sunrise: str
    sunset: str
    source: str = "aladhan"  # 'aladhan' | 'sunrise_sunset' | 'static_fallback'


class FastingActivateRequest(BaseModel):
    """Request body for /fasting/activate."""
    fasting_type: str = Field(
        pattern=r"^(ramadan|karva_chauth|navratri|ekadashi|jain_paryushana|custom)$"
    )
    start_date: date
    end_date: date | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    disclaimer_accepted: bool

    @model_validator(mode="after")
    def validate_disclaimer(self) -> "FastingActivateRequest":
        """Server-side enforcement: disclaimer MUST be explicitly True."""
        if not self.disclaimer_accepted:
            raise ValueError(
                "disclaimer_accepted must be true. "
                "Fasting mode cannot be activated without acknowledging the medical disclaimer."
            )
        return self


class ScheduleAdjustment(BaseModel):
    """A single dose schedule adjustment for fasting."""
    schedule_id: str
    medicine_name: str
    original_meal_anchor: str
    adjusted_meal_anchor: str
    reason: str
    severity_level: str = "info"  # 'info' | 'warning' | 'critical'
    physician_note_required: bool = False
    blocked: bool = False  # True for NEVER_AUTO_RESCHEDULE drugs


class FastingActivateResponse(BaseModel):
    """Response from /fasting/activate."""
    fasting_profile_id: str
    fasting_type: str
    adjustments: list[ScheduleAdjustment]
    blocked_medications: list[ScheduleAdjustment] = []
    pharmacist_reviewed: bool = False
    disclaimer: str = (
        "These schedule changes are general guidelines for fasting patients. "
        "They have not been reviewed by your personal physician. "
        "If you take insulin, have Type 1 Diabetes, or have had hypoglycemic episodes, "
        "DO NOT use fasting mode without explicit guidance from your doctor. "
        "Aujasya provides information only — not medical advice."
    )

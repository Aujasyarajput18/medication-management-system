"""
Aujasya — Caregiver Pydantic v2 Schemas
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


class InviteRequest(BaseModel):
    """POST /caregivers/invite request body."""

    caregiver_phone: str = Field(..., description="E.164 phone of caregiver to invite")

    @field_validator("caregiver_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+91[6-9]\d{9}$", v):
            raise ValueError("Must be a valid Indian mobile number (+91XXXXXXXXXX)")
        return v


class AcceptInviteRequest(BaseModel):
    """POST /caregivers/accept-invite request body."""

    link_id: UUID


class CaregiverLinkResponse(BaseModel):
    """Caregiver link data in API responses."""

    id: UUID
    patient_id: UUID
    caregiver_id: UUID
    status: str
    permissions: dict
    invited_at: datetime
    accepted_at: datetime | None = None

    model_config = {"from_attributes": True}


class PatientSummaryResponse(BaseModel):
    """Patient summary for caregiver dashboard."""

    patient_id: UUID
    name: str | None = None
    adherence_today_pct: float
    total_doses_today: int
    taken_doses_today: int
    last_seen: datetime | None = None
    next_dose_medicine: str | None = None
    next_dose_time: str | None = None
    current_streak: int
    has_overdue: bool

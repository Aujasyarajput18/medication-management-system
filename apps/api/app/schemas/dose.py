"""
Aujasya — Dose Pydantic v2 Schemas
[FIX-15] Calendar query uses month=YYYY-MM only, no separate year param.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


class DoseTakenRequest(BaseModel):
    """POST /doses/{id}/taken request body."""

    notes: str | None = Field(default=None, max_length=500)
    offline_sync: bool = False
    device_timestamp: datetime | None = None


class DoseSkippedRequest(BaseModel):
    """POST /doses/{id}/skipped request body."""

    skip_reason: str = Field(..., min_length=5, max_length=500)
    notes: str | None = Field(default=None, max_length=500)


class OfflineSyncMutation(BaseModel):
    """Single offline mutation in a batch sync."""

    dose_id: UUID
    action: str
    device_timestamp: datetime
    notes: str | None = None
    skip_reason: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in {"taken", "skipped"}:
            raise ValueError("Action must be 'taken' or 'skipped'")
        return v


class OfflineSyncRequest(BaseModel):
    """POST /doses/sync-offline request body."""

    mutations: list[OfflineSyncMutation] = Field(..., min_length=1, max_length=100)


class OfflineSyncResponse(BaseModel):
    """POST /doses/sync-offline response data."""

    synced: int
    skipped: int
    errors: list[str]


class DoseLogResponse(BaseModel):
    """Dose log data in API responses."""

    id: UUID
    schedule_id: UUID
    medicine_id: UUID
    patient_id: UUID
    scheduled_date: date
    meal_anchor: str
    status: str
    logged_at: datetime | None = None
    logged_by: UUID | None = None
    skip_reason: str | None = None
    notes: str | None = None
    offline_sync: bool
    expected_time: str | None = None
    medicine_name: str | None = None
    dosage_value: Decimal | None = None
    dosage_unit: str | None = None
    medicine_form: str | None = None

    model_config = {"from_attributes": True}


class DayAdherence(BaseModel):
    """Single day's adherence data for calendar view."""

    date: date
    total: int
    taken: int
    missed: int
    skipped: int
    adherence_pct: float


class CalendarResponse(BaseModel):
    """GET /doses/calendar response data. [FIX-15] Uses month=YYYY-MM only."""

    days: list[DayAdherence]
    month: str = Field(description="YYYY-MM format")


class StreakResponse(BaseModel):
    """GET /doses/streak response data."""

    current_streak: int
    longest_streak: int
    adherence_30d: float = Field(description="30-day rolling adherence percentage")

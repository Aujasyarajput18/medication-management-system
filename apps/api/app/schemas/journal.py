"""Aujasya — Side-Effect Journal Pydantic Schemas"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    """Request body for /journal/entry."""
    medicine_id: str | None = None
    dose_log_id: str | None = None
    symptom_text: str = Field(min_length=2, max_length=2000)
    severity: str = Field(pattern=r"^(mild|moderate|severe)$")
    onset_date: date
    input_method: str = Field(pattern=r"^(voice|text)$")
    voice_transcript: str | None = None


class JournalEntryResponse(BaseModel):
    """A single journal entry."""
    id: str
    medicine_id: str | None = None
    symptom_text: str
    symptom_normalized: list[str] = []
    severity: str
    onset_date: date
    resolved_date: date | None = None
    input_method: str
    is_flagged: bool = False
    flag_reason: str | None = None
    created_at: str


class PatternResult(BaseModel):
    """A detected side-effect pattern."""
    symptom: str
    count: int
    medicine_name: str | None = None
    first_occurrence: date
    last_occurrence: date


class JournalPatternsResponse(BaseModel):
    """Response from /journal/patterns."""
    patterns: list[PatternResult]
    period_days: int


class RefillStatus(BaseModel):
    """Refill status for a single medicine."""
    medicine_id: str
    brand_name: str
    remaining_quantity: int | None = None
    daily_dose_count: float
    days_remaining: float | None = None
    projected_runout_date: date | None = None
    alert_required: bool = False
    nearest_kendras: list[dict] = []


class RefillCountUpdate(BaseModel):
    """Request body for PATCH /refills/{medicine_id}/count."""
    remaining_quantity: int = Field(ge=0)
    update_source: str = Field(pattern=r"^(manual|barcode_scan)$")

"""
Aujasya — Medicine Pydantic v2 Schemas
[FIX-14] days_of_week validated: each element 0–6 (0=Sunday).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


VALID_DOSAGE_UNITS = {"mg", "ml", "mcg", "units"}
VALID_FORMS = {"tablet", "capsule", "syrup", "injection", "drops"}
VALID_MEAL_ANCHORS = {
    "before_breakfast", "with_breakfast", "after_breakfast",
    "before_lunch", "with_lunch", "after_lunch",
    "before_dinner", "with_dinner", "after_dinner",
    "at_bedtime", "on_waking", "any_time",
}


class ScheduleCreate(BaseModel):
    """Schedule creation within a medicine."""

    meal_anchor: str
    offset_minutes: int = Field(default=0, ge=-120, le=120)
    dose_quantity: Decimal = Field(default=Decimal("1"), gt=0, le=100)
    days_of_week: list[int] = Field(default=[0, 1, 2, 3, 4, 5, 6])
    reminder_level: int = Field(default=4, ge=1, le=4)

    @field_validator("meal_anchor")
    @classmethod
    def validate_meal_anchor(cls, v: str) -> str:
        if v not in VALID_MEAL_ANCHORS:
            raise ValueError(f"Invalid meal anchor. Must be one of: {VALID_MEAL_ANCHORS}")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """[FIX-14] Each value must be 0–6 (0=Sunday, matching Date.getDay())."""
        if not v:
            raise ValueError("days_of_week must have at least one day")
        for day in v:
            if day < 0 or day > 6:
                raise ValueError(f"Day {day} out of range. Must be 0 (Sunday) through 6 (Saturday)")
        return sorted(set(v))


class ScheduleResponse(BaseModel):
    """Schedule data in API responses."""

    id: UUID
    medicine_id: UUID
    meal_anchor: str
    offset_minutes: int
    dose_quantity: Decimal
    days_of_week: list[int]
    is_active: bool
    effective_from: date
    effective_until: date | None = None
    reminder_level: int

    model_config = {"from_attributes": True}


class MedicineCreate(BaseModel):
    """POST /medicines request body."""

    brand_name: str = Field(..., min_length=1, max_length=200)
    generic_name: str | None = Field(default=None, max_length=200)
    dosage_value: Decimal = Field(..., gt=0, le=99999)
    dosage_unit: str
    form: str
    start_date: date
    end_date: date | None = None
    prescribed_by: str | None = Field(default=None, max_length=200)
    instructions: str | None = Field(default=None, max_length=1000)
    total_quantity: int | None = Field(default=None, gt=0)
    schedules: list[ScheduleCreate] = Field(..., min_length=1, max_length=10)

    @field_validator("dosage_unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v not in VALID_DOSAGE_UNITS:
            raise ValueError(f"Invalid dosage unit. Must be one of: {VALID_DOSAGE_UNITS}")
        return v

    @field_validator("form")
    @classmethod
    def validate_form(cls, v: str) -> str:
        if v not in VALID_FORMS:
            raise ValueError(f"Invalid form. Must be one of: {VALID_FORMS}")
        return v


class MedicineUpdate(BaseModel):
    """PATCH /medicines/{id} — only allowed fields."""

    instructions: str | None = None
    end_date: date | None = None
    prescribed_by: str | None = None
    total_quantity: int | None = None


class MedicineResponse(BaseModel):
    """Medicine data in API responses."""

    id: UUID
    patient_id: UUID
    brand_name: str
    generic_name: str | None = None
    dosage_value: Decimal
    dosage_unit: str
    form: str
    is_active: bool
    start_date: date
    end_date: date | None = None
    prescribed_by: str | None = None
    instructions: str | None = None
    total_quantity: int | None = None
    remaining_quantity: int | None = None
    schedules: list[ScheduleResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}

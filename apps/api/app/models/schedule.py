"""
Aujasya — Schedule SQLAlchemy Model
Table: schedules
[FIX-14] days_of_week uses 0=Sunday convention matching Date.getDay().
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Schedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Defines when a medication should be taken.
    Uses meal anchors (before_breakfast, with_lunch, etc.) — not arbitrary clock times.
    
    [FIX-14] days_of_week convention:
        0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday,
        4=Thursday, 5=Friday, 6=Saturday
    This matches JavaScript's Date.getDay() and date-fns getDay().
    DO NOT use ISO week numbering (Monday=1).
    """

    __tablename__ = "schedules"

    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    meal_anchor: Mapped[str] = mapped_column(String(30), nullable=False)
    offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    dose_quantity: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, server_default="1",
    )
    # [FIX-14] Array of ints 0-6 (0=Sunday). Default: every day.
    days_of_week: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default="{0,1,2,3,4,5,6}",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_level: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="4",
    )

    # Relationships
    medicine: Mapped[Medicine] = relationship(back_populates="schedules")  # noqa: F821

    __table_args__ = (
        Index("idx_schedules_patient", "patient_id", "is_active"),
        Index("idx_schedules_medicine", "medicine_id"),
    )

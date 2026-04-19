"""
Aujasya — Dose Log SQLAlchemy Model
Table: dose_logs
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DoseLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Records each scheduled dose and its status.
    One log per dose — UNIQUE(schedule_id, scheduled_date, meal_anchor).
    [FIX-16] Generation uses INSERT ... ON CONFLICT DO NOTHING.
    """

    __tablename__ = "dose_logs"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False,
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_anchor: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    logged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    logged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    side_effects: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True,
    )
    offline_sync: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    device_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_date", "meal_anchor",
                         name="uq_dose_schedule_date_anchor"),
        Index("idx_dose_logs_patient_date", "patient_id", scheduled_date.desc()),
        Index("idx_dose_logs_status", "patient_id", "status", "scheduled_date"),
    )

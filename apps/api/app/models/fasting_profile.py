"""
Aujasya — Fasting Profile SQLAlchemy Models
Tables: fasting_profiles, fasting_schedule_overrides

Culturally-aware fasting mode for Ramadan, Karva Chauth, Navratri,
Ekadashi, Jain Paryushana, and custom fasting types.

pharmacist_reviewed is ALWAYS FALSE in Phase 2 — clinical validation gate.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FastingProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A patient's fasting configuration.

    fasting_type values:
        'ramadan', 'karva_chauth', 'navratri', 'ekadashi',
        'jain_paryushana', 'custom'

    pharmacist_reviewed is always FALSE in Phase 2.
    It becomes TRUE in Phase 3 when the medical advisory board signs off.
    Code MUST check this flag and show extra warning banners when FALSE.
    """

    __tablename__ = "fasting_profiles"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    fasting_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True,
    )
    disclaimer_accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    pharmacist_reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    custom_suhoor_time: Mapped[time | None] = mapped_column(
        Time, nullable=True,
    )
    custom_iftar_time: Mapped[time | None] = mapped_column(
        Time, nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    schedule_overrides: Mapped[list[FastingScheduleOverride]] = relationship(
        back_populates="fasting_profile", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "patient_id", "fasting_type", "start_date",
            name="uq_fasting_patient_type_date",
        ),
        Index("idx_fasting_patient", "patient_id", "is_active"),
    )


class FastingScheduleOverride(Base, UUIDPrimaryKeyMixin):
    """
    Records how a specific dose schedule was adjusted during fasting.
    Each override maps an original meal_anchor to an adjusted one
    with a clinical reason for the change.
    """

    __tablename__ = "fasting_schedule_overrides"

    fasting_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fasting_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False,
    )
    original_meal_anchor: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    adjusted_meal_anchor: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    adjustment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    physician_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False,
    )

    # Relationships
    fasting_profile: Mapped[FastingProfile] = relationship(
        back_populates="schedule_overrides",
    )

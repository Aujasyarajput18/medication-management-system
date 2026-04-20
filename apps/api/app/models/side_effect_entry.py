"""
Aujasya — Side Effect Entry SQLAlchemy Model
Table: side_effect_entries

Journal entries for patient-reported side effects.
Supports both voice (STT transcript) and text input.
NLP pattern detection flags recurring symptoms.
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
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SideEffectEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A single side-effect journal entry.

    severity values: 'mild', 'moderate', 'severe'
    input_method values: 'voice', 'text'

    Pattern detection:
        If the same normalized symptom appears 3+ times in 7 days,
        is_flagged is set to True and flag_reason describes the pattern.
    """

    __tablename__ = "side_effect_entries"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    dose_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dose_logs.id"), nullable=True,
    )
    medicine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=True,
    )
    symptom_text: Mapped[str] = mapped_column(Text, nullable=False)
    symptom_normalized: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True,
    )
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    onset_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default="CURRENT_DATE",
    )
    resolved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    input_method: Mapped[str] = mapped_column(String(10), nullable=False)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_journal_patient", "patient_id",
            onset_date.desc(),
        ),
        Index(
            "idx_journal_medicine", "medicine_id",
            onset_date.desc(),
        ),
    )

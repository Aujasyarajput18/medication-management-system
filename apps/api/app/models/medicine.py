"""
Aujasya — Medicine SQLAlchemy Model
Table: medicines
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Medicine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Medication record for a patient.
    prescribed_by and instructions are AES-256-GCM encrypted (stored as BYTEA).
    [FIX-19] Use load_only() to avoid loading BYTEA fields in list queries.
    """

    __tablename__ = "medicines"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    brand_name: Mapped[str] = mapped_column(Text, nullable=False)
    generic_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_ingredient: Mapped[str | None] = mapped_column(Text, nullable=True)
    dosage_value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    dosage_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    form: Mapped[str] = mapped_column(String(30), nullable=False)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    shape: Mapped[str | None] = mapped_column(String(30), nullable=True)
    imprint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_quantity: Mapped[int | None] = mapped_column(nullable=True)
    remaining_quantity: Mapped[int | None] = mapped_column(nullable=True)

    # AES-256-GCM encrypted fields
    prescribed_by: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    instructions: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    prescription_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fhir_medication_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped[User] = relationship(back_populates="medicines")  # noqa: F821
    schedules: Mapped[list[Schedule]] = relationship(  # noqa: F821
        back_populates="medicine", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_medicines_patient", "patient_id", "is_active"),
    )

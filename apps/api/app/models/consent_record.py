"""
Aujasya — Consent Record SQLAlchemy Model
Table: consent_records
DPDPA 2023 compliance — records every consent decision per purpose.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class ConsentRecord(Base, UUIDPrimaryKeyMixin):
    """
    Records individual consent decisions per user per purpose.
    DPDPA Article 7: consent must be explicit, not pre-checked.
    Each record captures the language, version, IP, and user agent
    at the time consent was given for full audit trail.
    """

    __tablename__ = "consent_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    consent_version: Mapped[str] = mapped_column(String(10), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(50), nullable=False)
    consented: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="consent_records")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "purpose_code", "consent_version",
                         name="uq_consent_user_purpose_version"),
        Index("idx_consent_user", "user_id", "purpose_code", "revoked_at"),
    )

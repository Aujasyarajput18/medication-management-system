"""
Aujasya — User-related SQLAlchemy Models
Tables: users, otp_sessions, refresh_tokens, user_meal_times
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Primary user table. Stores patients and caregivers.
    Sensitive fields (full_name, date_of_birth) are AES-256-GCM encrypted at rest.
    """

    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(
        String(15), unique=True, nullable=False, index=True,
    )
    phone_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    # AES-256-GCM encrypted fields stored as BYTEA
    full_name: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    date_of_birth: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    preferred_language: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default="hi",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="patient", index=True,
    )
    abha_id: Mapped[str | None] = mapped_column(String(17), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="Asia/Kolkata",
    )
    fcm_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    medicines: Mapped[list[Medicine]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan",
    )
    meal_times: Mapped[list[UserMealTime]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )
    push_subscriptions: Mapped[list[PushSubscription]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan",
    )
    consent_records: Mapped[list[ConsentRecord]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_users_phone", "phone_number"),
        Index("idx_users_role", "role"),
    )


class OtpSession(Base, UUIDPrimaryKeyMixin):
    """
    Stores OTP sessions for phone verification.
    OTP is bcrypt-hashed before storage — never stored in plaintext.
    """

    __tablename__ = "otp_sessions"

    phone_number: Mapped[str] = mapped_column(String(15), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_otp_phone_purpose", "phone_number", "purpose", "used"),
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    """
    Stores SHA-256 hashed refresh tokens.
    Implements token rotation: old tokens are revoked when a new one is issued.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    device_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_refresh_user", "user_id", "revoked"),
    )


class UserMealTime(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User's typical meal times. Used by the scheduling engine to convert
    meal anchors into actual clock times for reminders.
    """

    __tablename__ = "user_meal_times"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    meal_name: Mapped[str] = mapped_column(String(30), nullable=False)
    typical_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="Asia/Kolkata",
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="meal_times")

    __table_args__ = (
        # One meal time per user per meal name
        {"schema": None},
    )

    # UniqueConstraint defined in migration as UNIQUE(user_id, meal_name)

"""
Aujasya — Audit Log SQLAlchemy Model
Table: audit_logs
[FIX-12] This table was referenced but never defined in the original spec.

CRITICAL: This table is APPEND-ONLY.
- The ORM model does NOT define update() or delete() methods.
- The audit middleware writes INSERT only.
- Application-level enforcement prevents modification.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """
    Append-only audit log for all health data access.
    NO update_at column — this table is immutable after insertion.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    # NO updated_at — this table is append-only

    __table_args__ = (
        Index("idx_audit_user", "user_id", created_at.desc()),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

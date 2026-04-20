"""
Aujasya — AI Decision Log SQLAlchemy Model
Table: ai_decision_logs

Medico-legal audit trail for every AI-assisted clinical decision.
Every OCR parse, pill identification, drug interaction check, fasting
rescheduling, and generic lookup writes to this table with the full
chain of evidence: model version, confidence score, and user action.

This table is APPEND-ONLY. No updates or deletes.
DPDPA Purpose Limitation requires this audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AiDecisionLog(Base, UUIDPrimaryKeyMixin):
    """
    Append-only log of every AI-assisted decision.

    decision_type values:
        'ocr_scan'           — Prescription OCR (Tesseract or LLaVA)
        'pill_id'            — AI pill identification (TF.js or server-side)
        'interaction_check'  — Drug interaction check (RxNorm/OpenFDA)
        'fasting_reschedule' — Fasting mode dose rescheduling
        'generic_lookup'     — Generic drug discovery
        'voice_intent'       — Voice command intent classification

    user_action values:
        'accepted'  — User confirmed the AI suggestion
        'rejected'  — User dismissed the AI suggestion
        'modified'  — User edited the AI output before confirming
        'blocked'   — System blocked the action (e.g., insulin rescheduling)
        'pending'   — Awaiting user review
    """

    __tablename__ = "ai_decision_logs"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    decision_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    model_version: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True,
    )
    input_summary: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    output_summary: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
    )
    user_action: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    __table_args__ = (
        Index("idx_ai_decision_patient", "patient_id", created_at.desc()),
        Index("idx_ai_decision_type", "decision_type", created_at.desc()),
    )

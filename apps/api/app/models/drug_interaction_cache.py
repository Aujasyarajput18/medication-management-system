"""
Aujasya — Drug Interaction Cache SQLAlchemy Model
Table: drug_interaction_cache

Caches drug interaction results from RxNorm and OpenFDA APIs.
Cache TTL: 7 days. Keyed by ordered pair (rxcui_a, rxcui_b).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class DrugInteractionCache(Base, UUIDPrimaryKeyMixin):
    """
    Cached drug interaction result for a pair of RxNorm CUIs.

    severity values:
        'contraindicated' — drugs should NOT be taken together (RED)
        'major'           — significant risk, physician consultation (DEEP AMBER)
        'moderate'        — use with caution, monitor (AMBER)
        'minor'           — monitor but generally safe (YELLOW)

    source values: 'rxnorm', 'openfda', 'manual'
    """

    __tablename__ = "drug_interaction_cache"

    rxcui_a: Mapped[str] = mapped_column(String(20), nullable=False)
    rxcui_b: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(15), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("rxcui_a", "rxcui_b", name="uq_interaction_pair"),
        Index("idx_interaction_pair", "rxcui_a", "rxcui_b", "expires_at"),
    )

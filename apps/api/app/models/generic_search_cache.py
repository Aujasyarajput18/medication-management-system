"""
Aujasya — Generic Search Cache SQLAlchemy Model
Table: generic_search_cache

Caches generic drug alternative search results from Ekacare + PMBJP APIs.
Cache TTL: 24 hours. Keyed by normalized brand name.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class GenericSearchCache(Base, UUIDPrimaryKeyMixin):
    """
    Cached generic drug search result.

    alternatives is a JSONB array of:
    {
        name, manufacturer, mrp_per_unit, jan_aushadhi: bool,
        who_gmp: bool, nabl_certified: bool, pmbjp_code,
        bioequivalence_min: 90, bioequivalence_max: 110
    }

    source values: 'ekacare', 'pmbjp', 'combined'
    """

    __tablename__ = "generic_search_cache"

    brand_name_normalized: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True,
    )
    active_ingredient: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives: Mapped[dict] = mapped_column(JSONB, nullable=False)
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        Index(
            "idx_generic_cache_brand",
            "brand_name_normalized",
            "expires_at",
        ),
    )

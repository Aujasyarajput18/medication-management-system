"""
Aujasya — Generic Drug Discovery Service
Ranking algorithm with WHO-GMP/NABL trust score.
Combines Ekacare + PMBJP results with caching.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_decision_log import AiDecisionLog
from app.models.generic_search_cache import GenericSearchCache
from app.services.ekacare_service import EkacareService
from app.services.pmbjp_service import PmbjpService

logger = structlog.get_logger()

# WHO-GMP/NABL trust score weights
WEIGHT_WHO_GMP = 0.30
WEIGHT_NABL = 0.25
WEIGHT_JAN_AUSHADHI = 0.20
WEIGHT_PRICE = 0.15
WEIGHT_BIOEQUIVALENCE = 0.10


class GenericService:
    """Generic drug discovery with trust-based ranking."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.ekacare = EkacareService(redis)
        self.pmbjp = PmbjpService(redis)

    async def search_alternatives(
        self,
        brand_name: str,
        patient_id: uuid.UUID,
        lat: float | None = None,
        lng: float | None = None,
    ) -> dict:
        """Search for generic alternatives with trust-based ranking."""
        normalized = brand_name.strip().lower()

        # Check cache first
        cached = await self._get_cached(normalized)
        if cached:
            return cached

        # Fetch from both APIs
        ekacare_results = await self.ekacare.search_by_brand(brand_name)
        pmbjp_results = await self.pmbjp.search_generic(brand_name)

        # Merge and deduplicate
        alternatives = self._merge_results(ekacare_results, pmbjp_results)

        # Rank by trust score
        for alt in alternatives:
            alt["ranking_score"] = self._calculate_trust_score(alt)

        alternatives.sort(key=lambda x: x["ranking_score"], reverse=True)

        # Find nearest Jan Aushadhi Kendras
        if lat and lng:
            kendras = await self.pmbjp.find_nearest_kendras(lat, lng)
            for alt in alternatives:
                if alt.get("jan_aushadhi"):
                    alt["nearest_kendras"] = kendras[:3]

        result = {
            "brand": {"name": brand_name, "active_ingredient": "", "mrp_per_unit": 0},
            "alternatives": alternatives,
        }

        # Cache for 24 hours
        await self._cache_result(normalized, result)

        # Log AI decision
        await self._log_decision(patient_id, brand_name, len(alternatives))

        return result

    def _calculate_trust_score(self, alt: dict) -> float:
        """Calculate WHO-GMP/NABL weighted trust score."""
        score = 0.0
        if alt.get("who_gmp"):
            score += WEIGHT_WHO_GMP
        if alt.get("nabl_certified"):
            score += WEIGHT_NABL
        if alt.get("jan_aushadhi"):
            score += WEIGHT_JAN_AUSHADHI

        # Price score (lower = better, normalized)
        mrp = alt.get("mrp_per_unit", 0)
        if mrp > 0:
            score += WEIGHT_PRICE * max(0, 1 - (mrp / 100))

        # Bioequivalence (90-110% range = full score)
        bio_min = alt.get("bioequivalence_min", 90)
        bio_max = alt.get("bioequivalence_max", 110)
        if 80 <= bio_min <= 90 and 110 <= bio_max <= 125:
            score += WEIGHT_BIOEQUIVALENCE

        return round(score, 4)

    def _merge_results(self, ekacare: list, pmbjp: list) -> list:
        """Merge results from both APIs, deduplicating by name."""
        seen = set()
        merged = []
        for item in ekacare + pmbjp:
            name = item.get("name", "").lower()
            if name and name not in seen:
                seen.add(name)
                merged.append({
                    "name": item.get("name", ""),
                    "manufacturer": item.get("manufacturer", ""),
                    "mrp_per_unit": item.get("mrp_per_unit", 0),
                    "savings_percent": item.get("savings_percent", 0),
                    "jan_aushadhi": item.get("jan_aushadhi", False),
                    "who_gmp": item.get("who_gmp", False),
                    "nabl_certified": item.get("nabl_certified", False),
                    "pmbjp_code": item.get("pmbjp_code"),
                    "bioequivalence_min": item.get("bioequivalence_min", 90),
                    "bioequivalence_max": item.get("bioequivalence_max", 110),
                })
        return merged

    async def _get_cached(self, normalized: str) -> dict | None:
        now = datetime.now(timezone.utc)
        stmt = select(GenericSearchCache).where(
            GenericSearchCache.brand_name_normalized == normalized,
            GenericSearchCache.expires_at > now,
        )
        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()
        if cached:
            return cached.alternatives
        return None

    async def _cache_result(self, normalized: str, result: dict) -> None:
        now = datetime.now(timezone.utc)
        cache_entry = GenericSearchCache(
            brand_name_normalized=normalized,
            active_ingredient=result.get("brand", {}).get("active_ingredient", ""),
            alternatives=result,
            expires_at=now + timedelta(hours=24),
            source="combined",
        )
        self.db.add(cache_entry)
        await self.db.flush()

    async def _log_decision(self, patient_id: uuid.UUID, brand: str, count: int) -> None:
        log = AiDecisionLog(
            patient_id=patient_id,
            decision_type="generic_lookup",
            input_summary=f"Generic search: {brand}",
            output_summary={"alternatives_found": count},
            user_action="pending",
        )
        self.db.add(log)
        await self.db.flush()

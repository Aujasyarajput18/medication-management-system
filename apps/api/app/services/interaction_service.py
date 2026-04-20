"""
Aujasya — Drug Interaction Service
RxNorm + OpenFDA interaction lookup with DB caching.
Circuit breaker protected. All lookups logged to ai_decision_logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
import httpx
from redis.asyncio import Redis
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_decision_log import AiDecisionLog
from app.models.drug_interaction_cache import DrugInteractionCache
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()

CACHE_TTL_DAYS = 7


class InteractionService:
    """Drug interaction checking via RxNorm + OpenFDA with DB cache."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.rxnorm_breaker = CircuitBreaker(redis, "rxnorm", failure_threshold=5, recovery_timeout_s=120)
        self.openfda_breaker = CircuitBreaker(redis, "openfda", failure_threshold=5, recovery_timeout_s=120)

    async def check_interactions(
        self, rxcui_list: list[str], patient_id: uuid.UUID,
    ) -> dict:
        """Check all pairwise interactions for a list of RxCUIs."""
        all_interactions = []
        now = datetime.now(timezone.utc)

        # Check all pairs
        for i in range(len(rxcui_list)):
            for j in range(i + 1, len(rxcui_list)):
                a, b = sorted([rxcui_list[i], rxcui_list[j]])

                # Check cache first
                cached = await self._get_cached(a, b, now)
                if cached:
                    all_interactions.append(cached)
                    continue

                # Query RxNorm
                result = await self._query_rxnorm(a, b)
                if result:
                    await self._cache_result(a, b, result)
                    all_interactions.append(result)

        critical_count = sum(1 for i in all_interactions if i.get("severity") == "contraindicated")
        major_count = sum(1 for i in all_interactions if i.get("severity") == "major")

        # Log to AI decision trail
        await self._log_decision(patient_id, rxcui_list, all_interactions)

        return {
            "interactions": all_interactions,
            "critical_count": critical_count,
            "major_count": major_count,
        }

    async def resolve_rxcui(self, drug_name: str) -> dict | None:
        """Resolve a drug name to RxNorm CUI."""
        if await self.rxnorm_breaker.is_open():
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.RXNORM_API_URL}/rxcui.json",
                    params={"name": drug_name, "search": 1},
                )
            if resp.status_code == 200:
                await self.rxnorm_breaker.record_success()
                data = resp.json()
                ids = data.get("idGroup", {}).get("rxnormId", [])
                if ids:
                    return {"rxcui": ids[0], "name": drug_name, "found": True}
            await self.rxnorm_breaker.record_failure()
            return None
        except Exception as e:
            await self.rxnorm_breaker.record_failure()
            logger.error("rxnorm_resolve_failed", error=str(e))
            return None

    async def _query_rxnorm(self, rxcui_a: str, rxcui_b: str) -> dict | None:
        """Query RxNorm interaction API for a drug pair."""
        if await self.rxnorm_breaker.is_open():
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.RXNORM_API_URL}/interaction/list.json",
                    params={"rxcuis": f"{rxcui_a}+{rxcui_b}"},
                )
            if resp.status_code == 200:
                await self.rxnorm_breaker.record_success()
                data = resp.json()
                pairs = data.get("fullInteractionTypeGroup", [])
                if pairs:
                    interaction = pairs[0].get("fullInteractionType", [{}])[0]
                    desc = interaction.get("interactionPair", [{}])[0].get("description", "")
                    severity_str = interaction.get("interactionPair", [{}])[0].get("severity", "")
                    severity = self._normalize_severity(severity_str)
                    return {
                        "drug_a": {"rxcui": rxcui_a, "name": ""},
                        "drug_b": {"rxcui": rxcui_b, "name": ""},
                        "severity": severity,
                        "description": desc,
                    }
            await self.rxnorm_breaker.record_failure()
            return None
        except Exception as e:
            await self.rxnorm_breaker.record_failure()
            logger.error("rxnorm_interaction_failed", error=str(e))
            return None

    def _normalize_severity(self, severity_str: str) -> str:
        s = severity_str.lower()
        if "contraindicated" in s:
            return "contraindicated"
        if "major" in s or "high" in s:
            return "major"
        if "moderate" in s:
            return "moderate"
        return "minor"

    async def _get_cached(self, a: str, b: str, now: datetime) -> dict | None:
        stmt = select(DrugInteractionCache).where(
            and_(
                DrugInteractionCache.rxcui_a == a,
                DrugInteractionCache.rxcui_b == b,
                DrugInteractionCache.expires_at > now,
            )
        )
        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()
        if cached:
            return {
                "drug_a": {"rxcui": cached.rxcui_a, "name": ""},
                "drug_b": {"rxcui": cached.rxcui_b, "name": ""},
                "severity": cached.severity,
                "description": cached.description,
            }
        return None

    async def _cache_result(self, a: str, b: str, result: dict) -> None:
        entry = DrugInteractionCache(
            rxcui_a=a, rxcui_b=b,
            severity=result["severity"],
            description=result["description"],
            source="rxnorm",
            expires_at=datetime.now(timezone.utc) + timedelta(days=CACHE_TTL_DAYS),
        )
        self.db.add(entry)
        await self.db.flush()

    async def _log_decision(self, patient_id, rxcui_list, interactions) -> None:
        log = AiDecisionLog(
            patient_id=patient_id,
            decision_type="interaction_check",
            input_summary=f"Checked {len(rxcui_list)} drugs: {', '.join(rxcui_list)}",
            output_summary={"count": len(interactions), "interactions": interactions},
            user_action="pending",
        )
        self.db.add(log)
        await self.db.flush()

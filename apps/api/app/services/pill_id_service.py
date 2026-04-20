"""
Aujasya — Pill Identification Service
Server-side pill ID with DB matching. AI decision audit logging.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_decision_log import AiDecisionLog
from app.models.medicine import Medicine

logger = structlog.get_logger()


class PillIdService:
    """Server-side pill identification and matching."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_by_appearance(
        self,
        patient_id: uuid.UUID,
        color: str | None = None,
        shape: str | None = None,
        imprint: str | None = None,
    ) -> list[dict]:
        """Match pill by visual attributes against patient's medicines."""
        stmt = select(Medicine).where(
            Medicine.patient_id == patient_id,
            Medicine.is_active == True,  # noqa: E712
        )

        if color:
            stmt = stmt.where(Medicine.color.ilike(f"%{color}%"))
        if shape:
            stmt = stmt.where(Medicine.shape.ilike(f"%{shape}%"))
        if imprint:
            stmt = stmt.where(Medicine.imprint.ilike(f"%{imprint}%"))

        result = await self.db.execute(stmt)
        medicines = result.scalars().all()

        candidates = []
        for m in medicines:
            score = 0.0
            matches = 0
            if color and m.color and color.lower() in m.color.lower():
                score += 0.3
                matches += 1
            if shape and m.shape and shape.lower() in m.shape.lower():
                score += 0.3
                matches += 1
            if imprint and m.imprint and imprint.lower() in m.imprint.lower():
                score += 0.4
                matches += 1

            if matches > 0:
                candidates.append({
                    "drug_name": m.brand_name,
                    "confidence": min(score, 1.0),
                    "color": m.color,
                    "shape": m.shape,
                    "imprint": m.imprint,
                    "matched_medicine_id": str(m.id),
                })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # Log to AI decision trail
        await self._log_decision(patient_id, candidates)
        return candidates[:5]

    async def _log_decision(self, patient_id: uuid.UUID, candidates: list[dict]) -> None:
        top_confidence = Decimal(str(candidates[0]["confidence"])) if candidates else Decimal("0")
        log = AiDecisionLog(
            patient_id=patient_id,
            decision_type="pill_id",
            model_version=settings.PILL_MODEL_VERSION,
            confidence=top_confidence,
            input_summary="Pill appearance matching",
            output_summary={"candidates_count": len(candidates), "top_3": candidates[:3]},
            user_action="pending",
        )
        self.db.add(log)
        await self.db.flush()

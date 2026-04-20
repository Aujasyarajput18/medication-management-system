"""
Aujasya — Refill Intelligence Service
Calculates days-remaining, projected runout dates, and nearest Jan Aushadhi.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import structlog
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.services.pmbjp_service import PmbjpService

logger = structlog.get_logger()


class RefillService:
    """Refill tracking and projection."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.pmbjp = PmbjpService(redis)

    async def get_refill_status(
        self,
        patient_id: uuid.UUID,
        lat: float | None = None,
        lng: float | None = None,
    ) -> list[dict]:
        """Get refill status for all active medicines."""
        stmt = select(Medicine).where(
            Medicine.patient_id == patient_id,
            Medicine.is_active == True,  # noqa: E712
            Medicine.remaining_quantity.is_not(None),
        )
        result = await self.db.execute(stmt)
        medicines = result.scalars().all()

        statuses = []
        for med in medicines:
            daily_doses = await self._get_daily_dose_count(med.id)
            days_remaining = None
            runout_date = None
            alert = False

            if daily_doses > 0 and med.remaining_quantity is not None:
                days_remaining = med.remaining_quantity / daily_doses
                runout_date = date.today() + timedelta(days=int(days_remaining))
                alert = days_remaining <= med.refill_threshold_days

            status = {
                "medicine_id": str(med.id),
                "brand_name": med.brand_name,
                "remaining_quantity": med.remaining_quantity,
                "daily_dose_count": daily_doses,
                "days_remaining": round(days_remaining, 1) if days_remaining else None,
                "projected_runout_date": runout_date.isoformat() if runout_date else None,
                "alert_required": alert,
                "nearest_kendras": [],
            }

            # Find nearest Jan Aushadhi if refill needed and location provided
            if alert and lat and lng:
                kendras = await self.pmbjp.find_nearest_kendras(lat, lng)
                status["nearest_kendras"] = kendras[:3]

            statuses.append(status)

        return statuses

    async def update_count(
        self, medicine_id: uuid.UUID, remaining: int,
    ) -> None:
        """Update remaining quantity for a medicine."""
        stmt = select(Medicine).where(Medicine.id == medicine_id)
        result = await self.db.execute(stmt)
        med = result.scalar_one_or_none()
        if med:
            med.remaining_quantity = remaining

    async def _get_daily_dose_count(self, medicine_id: uuid.UUID) -> float:
        """Calculate how many doses per day from active schedules."""
        stmt = select(func.count()).where(
            and_(
                Schedule.medicine_id == medicine_id,
                Schedule.is_active == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        return float(result.scalar() or 0)

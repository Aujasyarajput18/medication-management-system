"""
Aujasya — Dose Service
Handles dose logging, status updates, offline sync, calendar, and streaks.
[FIX-15] Calendar uses month=YYYY-MM only.
[FIX-16] generate_daily_doses uses INSERT ... ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta

import structlog
from sqlalchemy import select, text, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.dose_log import DoseLog
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.schemas.dose import (
    CalendarResponse,
    DayAdherence,
    DoseLogResponse,
    DoseSkippedRequest,
    DoseTakenRequest,
    OfflineSyncRequest,
    OfflineSyncResponse,
    StreakResponse,
)
from app.utils.timezone import now_ist, today_ist

logger = structlog.get_logger()


class DoseService:
    """Handles all dose-related operations."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def get_today_doses(self, patient_id: uuid.UUID) -> list[DoseLogResponse]:
        """Get all dose logs for today grouped by meal anchor."""
        today = today_ist()

        stmt = (
            select(DoseLog, Medicine)
            .join(Medicine, DoseLog.medicine_id == Medicine.id)
            .options(
                load_only(
                    Medicine.brand_name,
                    Medicine.dosage_value,
                    Medicine.dosage_unit,
                    Medicine.form,
                ),
            )
            .where(
                DoseLog.patient_id == patient_id,
                DoseLog.scheduled_date == today,
            )
            .order_by(DoseLog.meal_anchor)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            DoseLogResponse(
                id=dose.id,
                schedule_id=dose.schedule_id,
                medicine_id=dose.medicine_id,
                patient_id=dose.patient_id,
                scheduled_date=dose.scheduled_date,
                meal_anchor=dose.meal_anchor,
                status=dose.status,
                logged_at=dose.logged_at,
                logged_by=dose.logged_by,
                skip_reason=dose.skip_reason,
                notes=dose.notes,
                offline_sync=dose.offline_sync,
                medicine_name=med.brand_name,
                dosage_value=med.dosage_value,
                dosage_unit=med.dosage_unit,
                medicine_form=med.form,
            )
            for dose, med in rows
        ]

    async def mark_taken(
        self,
        dose_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: DoseTakenRequest,
        logged_by: uuid.UUID | None = None,
    ) -> DoseLogResponse:
        """Mark a dose as taken. Cancels any pending escalation."""
        dose = await self._get_dose(dose_id, patient_id)

        dose.status = "taken"
        dose.logged_at = now_ist()
        dose.logged_by = logged_by or patient_id
        dose.notes = data.notes
        dose.offline_sync = data.offline_sync
        dose.device_timestamp = data.device_timestamp

        await self.db.flush()

        # Cancel escalation reminders
        if self.redis:
            await self.redis.delete(f"escalation:{dose_id}:level")

        logger.info("dose_taken", dose_id=str(dose_id), patient_id=str(patient_id))

        return await self._dose_to_response(dose)

    async def mark_skipped(
        self,
        dose_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: DoseSkippedRequest,
    ) -> DoseLogResponse:
        """Mark a dose as skipped with a reason (min 5 chars)."""
        dose = await self._get_dose(dose_id, patient_id)

        dose.status = "skipped"
        dose.logged_at = now_ist()
        dose.logged_by = patient_id
        dose.skip_reason = data.skip_reason
        dose.notes = data.notes

        await self.db.flush()

        # Cancel escalation
        if self.redis:
            await self.redis.delete(f"escalation:{dose_id}:level")

        logger.info("dose_skipped", dose_id=str(dose_id), reason=data.skip_reason[:20])

        return await self._dose_to_response(dose)

    async def sync_offline(
        self, patient_id: uuid.UUID, data: OfflineSyncRequest
    ) -> OfflineSyncResponse:
        """
        Process batch offline mutations.
        Conflict resolution: "last device_timestamp wins."
        """
        synced = 0
        skipped_count = 0
        errors: list[str] = []

        for mutation in data.mutations:
            try:
                dose = await self._get_dose(mutation.dose_id, patient_id)

                # Conflict resolution: if already logged with a later timestamp, skip
                if dose.device_timestamp and mutation.device_timestamp:
                    if dose.device_timestamp >= mutation.device_timestamp:
                        skipped_count += 1
                        continue

                if mutation.action == "taken":
                    dose.status = "taken"
                    dose.logged_at = mutation.device_timestamp
                    dose.notes = mutation.notes
                elif mutation.action == "skipped":
                    dose.status = "skipped"
                    dose.logged_at = mutation.device_timestamp
                    dose.skip_reason = mutation.skip_reason
                    dose.notes = mutation.notes

                dose.offline_sync = True
                dose.device_timestamp = mutation.device_timestamp
                dose.logged_by = patient_id
                synced += 1

            except ValueError:
                errors.append(f"Dose {mutation.dose_id} not found")
            except Exception as e:
                errors.append(f"Error syncing dose {mutation.dose_id}: {str(e)}")

        await self.db.flush()

        logger.info(
            "offline_sync_completed",
            patient_id=str(patient_id),
            synced=synced,
            skipped=skipped_count,
            errors=len(errors),
        )

        return OfflineSyncResponse(synced=synced, skipped=skipped_count, errors=errors)

    async def get_calendar(
        self, patient_id: uuid.UUID, month: str
    ) -> CalendarResponse:
        """
        Get calendar adherence data for a month.
        [FIX-15] month param format: YYYY-MM (no separate year param).
        """
        try:
            year, month_num = month.split("-")
            start_date = date(int(year), int(month_num), 1)
        except (ValueError, IndexError):
            raise ValueError("Month must be in YYYY-MM format")

        # Get last day of month
        if int(month_num) == 12:
            end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(int(year), int(month_num) + 1, 1) - timedelta(days=1)

        stmt = (
            select(
                DoseLog.scheduled_date,
                DoseLog.status,
                func.count().label("count"),
            )
            .where(
                DoseLog.patient_id == patient_id,
                DoseLog.scheduled_date >= start_date,
                DoseLog.scheduled_date <= end_date,
            )
            .group_by(DoseLog.scheduled_date, DoseLog.status)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Aggregate by day
        day_data: dict[date, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "taken": 0, "missed": 0, "skipped": 0}
        )

        for row in rows:
            sd = row.scheduled_date
            status = row.status
            count = row.count

            day_data[sd]["total"] += count
            if status in day_data[sd]:
                day_data[sd][status] += count

        # Build response
        days = []
        current = start_date
        while current <= end_date:
            d = day_data[current]
            total = d["total"]
            adherence = (d["taken"] / total * 100) if total > 0 else 0.0
            days.append(
                DayAdherence(
                    date=current,
                    total=total,
                    taken=d["taken"],
                    missed=d["missed"],
                    skipped=d["skipped"],
                    adherence_pct=round(adherence, 1),
                )
            )
            current += timedelta(days=1)

        return CalendarResponse(days=days, month=f"{year}-{month_num}")

    async def get_streak(self, patient_id: uuid.UUID) -> StreakResponse:
        """
        Calculate current streak (consecutive days with ≥80% adherence),
        longest streak, and 30-day rolling adherence.
        """
        today = today_ist()
        thirty_days_ago = today - timedelta(days=30)

        # Get all dose logs for last 90 days (for streak calculation)
        ninety_days_ago = today - timedelta(days=90)
        stmt = (
            select(
                DoseLog.scheduled_date,
                DoseLog.status,
                func.count().label("count"),
            )
            .where(
                DoseLog.patient_id == patient_id,
                DoseLog.scheduled_date >= ninety_days_ago,
                DoseLog.scheduled_date <= today,
            )
            .group_by(DoseLog.scheduled_date, DoseLog.status)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build daily adherence map
        daily: dict[date, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "taken": 0}
        )
        for row in rows:
            daily[row.scheduled_date]["total"] += row.count
            if row.status == "taken":
                daily[row.scheduled_date]["taken"] += row.count

        # Calculate current streak (backwards from today)
        current_streak = 0
        check_date = today
        while check_date >= ninety_days_ago:
            d = daily.get(check_date)
            if d and d["total"] > 0:
                adherence = d["taken"] / d["total"]
                if adherence >= 0.8:
                    current_streak += 1
                else:
                    break
            elif d is None:
                # No doses for this day (no active medicines), continue streak
                pass
            check_date -= timedelta(days=1)

        # Calculate longest streak
        longest_streak = 0
        current_run = 0
        check_date = ninety_days_ago
        while check_date <= today:
            d = daily.get(check_date)
            if d and d["total"] > 0:
                adherence = d["taken"] / d["total"]
                if adherence >= 0.8:
                    current_run += 1
                    longest_streak = max(longest_streak, current_run)
                else:
                    current_run = 0
            check_date += timedelta(days=1)

        # 30-day rolling adherence
        total_30d = 0
        taken_30d = 0
        for d in range(31):
            check = today - timedelta(days=d)
            if check in daily:
                total_30d += daily[check]["total"]
                taken_30d += daily[check]["taken"]

        adherence_30d = (taken_30d / total_30d * 100) if total_30d > 0 else 0.0

        return StreakResponse(
            current_streak=current_streak,
            longest_streak=longest_streak,
            adherence_30d=round(adherence_30d, 1),
        )

    async def _get_dose(
        self, dose_id: uuid.UUID, patient_id: uuid.UUID
    ) -> DoseLog:
        """Get a single dose log, verifying ownership."""
        stmt = select(DoseLog).where(
            DoseLog.id == dose_id,
            DoseLog.patient_id == patient_id,
        )
        result = await self.db.execute(stmt)
        dose = result.scalar_one_or_none()

        if dose is None:
            raise ValueError("Dose not found")

        return dose

    async def _dose_to_response(self, dose: DoseLog) -> DoseLogResponse:
        """Convert dose log to response."""
        return DoseLogResponse(
            id=dose.id,
            schedule_id=dose.schedule_id,
            medicine_id=dose.medicine_id,
            patient_id=dose.patient_id,
            scheduled_date=dose.scheduled_date,
            meal_anchor=dose.meal_anchor,
            status=dose.status,
            logged_at=dose.logged_at,
            logged_by=dose.logged_by,
            skip_reason=dose.skip_reason,
            notes=dose.notes,
            offline_sync=dose.offline_sync,
        )

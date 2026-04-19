"""
Aujasya — Medicine Service
CRUD for medicines + schedule generation + dose log pre-generation.
[FIX-16] Dose pre-generation uses INSERT ... ON CONFLICT DO NOTHING.
[FIX-19] List queries use load_only() to avoid loading encrypted BYTEA fields.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.models.dose_log import DoseLog
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.medicine import MedicineCreate, MedicineResponse, MedicineUpdate
from app.services.encryption_service import encryption_service
from app.utils.timezone import today_ist

logger = structlog.get_logger()


class MedicineService:
    """Handles medicine CRUD with schedule and dose log generation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_medicine(
        self, patient_id: uuid.UUID, data: MedicineCreate
    ) -> MedicineResponse:
        """
        Create a medicine with schedules and pre-generate 30 days of dose logs.
        [FIX-16] Uses INSERT ... ON CONFLICT DO NOTHING for dose log batch insert.
        """
        # Create medicine
        medicine = Medicine(
            patient_id=patient_id,
            brand_name=data.brand_name,
            generic_name=data.generic_name,
            dosage_value=float(data.dosage_value),
            dosage_unit=data.dosage_unit,
            form=data.form,
            start_date=data.start_date,
            end_date=data.end_date,
            total_quantity=data.total_quantity,
            remaining_quantity=data.total_quantity,
            # Encrypt sensitive fields
            prescribed_by=(
                encryption_service.encrypt_bytes(data.prescribed_by, "prescribed_by")
                if data.prescribed_by
                else None
            ),
            instructions=(
                encryption_service.encrypt_bytes(data.instructions, "instructions")
                if data.instructions
                else None
            ),
        )
        self.db.add(medicine)
        await self.db.flush()

        # Create schedules
        schedules: list[Schedule] = []
        for sched_data in data.schedules:
            schedule = Schedule(
                medicine_id=medicine.id,
                patient_id=patient_id,
                meal_anchor=sched_data.meal_anchor,
                offset_minutes=sched_data.offset_minutes,
                dose_quantity=float(sched_data.dose_quantity),
                days_of_week=sched_data.days_of_week,
                effective_from=data.start_date,
                effective_until=data.end_date,
                reminder_level=sched_data.reminder_level,
            )
            self.db.add(schedule)
            schedules.append(schedule)

        await self.db.flush()

        # Pre-generate 30 days of dose logs
        await self._generate_dose_logs(
            medicine=medicine,
            schedules=schedules,
            patient_id=patient_id,
            start_date=data.start_date,
            days=30,
        )

        logger.info(
            "medicine_created",
            medicine_id=str(medicine.id),
            patient_id=str(patient_id),
            schedules_count=len(schedules),
        )

        return await self.get_medicine(medicine.id, patient_id)

    async def get_medicine(
        self, medicine_id: uuid.UUID, patient_id: uuid.UUID
    ) -> MedicineResponse:
        """Get a single medicine with all details (including decrypted fields)."""
        stmt = (
            select(Medicine)
            .options(selectinload(Medicine.schedules))
            .where(Medicine.id == medicine_id, Medicine.patient_id == patient_id)
        )
        result = await self.db.execute(stmt)
        medicine = result.scalar_one_or_none()

        if medicine is None:
            raise ValueError("Medicine not found")

        return self._to_response(medicine, decrypt=True)

    async def list_medicines(
        self, patient_id: uuid.UUID, include_inactive: bool = False
    ) -> list[MedicineResponse]:
        """
        List all medicines for a patient.
        [FIX-19] Uses load_only() — does NOT load encrypted BYTEA fields.
        """
        stmt = (
            select(Medicine)
            .options(
                load_only(
                    Medicine.id,
                    Medicine.patient_id,
                    Medicine.brand_name,
                    Medicine.generic_name,
                    Medicine.dosage_value,
                    Medicine.dosage_unit,
                    Medicine.form,
                    Medicine.is_active,
                    Medicine.start_date,
                    Medicine.end_date,
                    Medicine.total_quantity,
                    Medicine.remaining_quantity,
                    Medicine.created_at,
                ),
                selectinload(Medicine.schedules),
            )
            .where(Medicine.patient_id == patient_id)
            .order_by(Medicine.created_at.desc())
        )

        if not include_inactive:
            stmt = stmt.where(Medicine.is_active == True)  # noqa: E712

        result = await self.db.execute(stmt)
        medicines = result.scalars().all()

        return [self._to_response(m, decrypt=False) for m in medicines]

    async def update_medicine(
        self, medicine_id: uuid.UUID, patient_id: uuid.UUID, data: MedicineUpdate
    ) -> MedicineResponse:
        """Update allowed medicine fields."""
        stmt = select(Medicine).where(
            Medicine.id == medicine_id, Medicine.patient_id == patient_id
        )
        result = await self.db.execute(stmt)
        medicine = result.scalar_one_or_none()

        if medicine is None:
            raise ValueError("Medicine not found")

        if data.instructions is not None:
            medicine.instructions = encryption_service.encrypt_bytes(
                data.instructions, "instructions"
            )
        if data.prescribed_by is not None:
            medicine.prescribed_by = encryption_service.encrypt_bytes(
                data.prescribed_by, "prescribed_by"
            )
        if data.end_date is not None:
            medicine.end_date = data.end_date
        if data.total_quantity is not None:
            medicine.total_quantity = data.total_quantity

        await self.db.flush()
        return await self.get_medicine(medicine_id, patient_id)

    async def deactivate_medicine(
        self, medicine_id: uuid.UUID, patient_id: uuid.UUID
    ) -> None:
        """Soft-delete a medicine and deactivate its schedules."""
        stmt = select(Medicine).where(
            Medicine.id == medicine_id, Medicine.patient_id == patient_id
        )
        result = await self.db.execute(stmt)
        medicine = result.scalar_one_or_none()

        if medicine is None:
            raise ValueError("Medicine not found")

        medicine.is_active = False

        # Deactivate all schedules
        sched_stmt = select(Schedule).where(Schedule.medicine_id == medicine_id)
        sched_result = await self.db.execute(sched_stmt)
        for schedule in sched_result.scalars():
            schedule.is_active = False

        await self.db.flush()

        logger.info(
            "medicine_deactivated",
            medicine_id=str(medicine_id),
            patient_id=str(patient_id),
        )

    async def _generate_dose_logs(
        self,
        medicine: Medicine,
        schedules: list[Schedule],
        patient_id: uuid.UUID,
        start_date: date,
        days: int = 30,
    ) -> None:
        """
        Pre-generate pending dose logs for the given number of days.
        [FIX-16] Uses raw SQL INSERT ... ON CONFLICT DO NOTHING to handle
        overlap with nightly Celery generate_daily_doses task.
        """
        values_list: list[dict] = []

        for day_offset in range(days):
            target_date = start_date + timedelta(days=day_offset)
            day_of_week = target_date.weekday()
            # Convert Python weekday (Mon=0) to our convention (Sun=0) [FIX-14]
            js_day = (day_of_week + 1) % 7

            for schedule in schedules:
                if js_day in schedule.days_of_week:
                    # Check end date
                    if medicine.end_date and target_date > medicine.end_date:
                        continue

                    values_list.append(
                        {
                            "schedule_id": str(schedule.id),
                            "medicine_id": str(medicine.id),
                            "patient_id": str(patient_id),
                            "scheduled_date": target_date.isoformat(),
                            "meal_anchor": schedule.meal_anchor,
                            "status": "pending",
                        }
                    )

        if not values_list:
            return

        # [FIX-16] Batch insert with ON CONFLICT DO NOTHING
        # This prevents UniqueConstraint violations when the nightly
        # generate_daily_doses Celery task runs during the first 30 days
        stmt = text("""
            INSERT INTO dose_logs (id, schedule_id, medicine_id, patient_id,
                                   scheduled_date, meal_anchor, status, created_at, updated_at)
            VALUES (uuid_generate_v4(), :schedule_id, :medicine_id, :patient_id,
                    :scheduled_date, :meal_anchor, :status, NOW(), NOW())
            ON CONFLICT (schedule_id, scheduled_date, meal_anchor) DO NOTHING
        """)

        for values in values_list:
            await self.db.execute(stmt, values)

        await self.db.flush()

        logger.info(
            "dose_logs_pre_generated",
            medicine_id=str(medicine.id),
            count=len(values_list),
            days=days,
        )

    def _to_response(self, medicine: Medicine, decrypt: bool = False) -> MedicineResponse:
        """Convert ORM model to response schema."""
        prescribed_by = None
        instructions = None

        if decrypt:
            prescribed_by = encryption_service.decrypt_bytes(
                medicine.prescribed_by, "prescribed_by"
            )
            instructions = encryption_service.decrypt_bytes(
                medicine.instructions, "instructions"
            )

        schedules = []
        if hasattr(medicine, "schedules") and medicine.schedules:
            from app.schemas.medicine import ScheduleResponse
            schedules = [
                ScheduleResponse.model_validate(s) for s in medicine.schedules
            ]

        return MedicineResponse(
            id=medicine.id,
            patient_id=medicine.patient_id,
            brand_name=medicine.brand_name,
            generic_name=medicine.generic_name,
            dosage_value=medicine.dosage_value,
            dosage_unit=medicine.dosage_unit,
            form=medicine.form,
            is_active=medicine.is_active,
            start_date=medicine.start_date,
            end_date=medicine.end_date,
            prescribed_by=prescribed_by,
            instructions=instructions,
            total_quantity=medicine.total_quantity,
            remaining_quantity=medicine.remaining_quantity,
            schedules=schedules,
            created_at=medicine.created_at,
        )

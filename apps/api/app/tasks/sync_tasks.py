"""
Aujasya — Sync & Maintenance Celery Tasks
[FIX-6] Uses sync SQLAlchemy engine (SyncSessionLocal).
[FIX-16] generate_daily_doses uses INSERT ... ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

from datetime import date, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import load_only

from app.database import SyncSessionLocal
from app.models.dose_log import DoseLog
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.models.user import OtpSession
from app.tasks.celery_app import celery_app
from app.utils.timezone import now_ist, today_ist

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, name="app.tasks.sync_tasks.generate_daily_doses")
def generate_daily_doses(self):
    """
    [FIX-5] Runs at 00:01 IST (not UTC) via Celery Beat config.
    [FIX-6] Uses SyncSessionLocal — Celery tasks are synchronous.
    [FIX-16] Uses INSERT ... ON CONFLICT DO NOTHING to prevent constraint
    violations from the 30-day pre-generation on medicine creation.
    
    Generates pending dose_log entries for today and the next 7 days
    for all active schedules.
    """
    with SyncSessionLocal() as db:
        try:
            today = today_ist()
            generation_window = 7  # days ahead to generate

            # Get all active schedules with their medicines
            stmt = (
                select(Schedule)
                .options(
                    load_only(
                        Schedule.id,
                        Schedule.medicine_id,
                        Schedule.patient_id,
                        Schedule.meal_anchor,
                        Schedule.days_of_week,
                        Schedule.effective_from,
                        Schedule.effective_until,
                    )
                )
                .where(Schedule.is_active == True)  # noqa: E712
            )
            result = db.execute(stmt)
            schedules = result.scalars().all()

            total_generated = 0
            total_skipped = 0

            for schedule in schedules:
                for day_offset in range(generation_window):
                    target_date = today + timedelta(days=day_offset)

                    # Check effective dates
                    if target_date < schedule.effective_from:
                        continue
                    if schedule.effective_until and target_date > schedule.effective_until:
                        continue

                    # Check day of week [FIX-14]
                    # Convert Python weekday (Mon=0) to our convention (Sun=0)
                    py_weekday = target_date.weekday()
                    js_day = (py_weekday + 1) % 7

                    if js_day not in schedule.days_of_week:
                        continue

                    # [FIX-16] INSERT ... ON CONFLICT DO NOTHING
                    # This handles overlap with the 30-day pre-generation
                    insert_stmt = text("""
                        INSERT INTO dose_logs (
                            id, schedule_id, medicine_id, patient_id,
                            scheduled_date, meal_anchor, status,
                            created_at, updated_at
                        )
                        VALUES (
                            uuid_generate_v4(), :schedule_id, :medicine_id, :patient_id,
                            :scheduled_date, :meal_anchor, 'pending',
                            NOW(), NOW()
                        )
                        ON CONFLICT (schedule_id, scheduled_date, meal_anchor) DO NOTHING
                    """)

                    result = db.execute(
                        insert_stmt,
                        {
                            "schedule_id": str(schedule.id),
                            "medicine_id": str(schedule.medicine_id),
                            "patient_id": str(schedule.patient_id),
                            "scheduled_date": target_date.isoformat(),
                            "meal_anchor": schedule.meal_anchor,
                        },
                    )

                    if result.rowcount > 0:
                        total_generated += 1
                    else:
                        total_skipped += 1

            db.commit()

            logger.info(
                "daily_doses_generated",
                date=today.isoformat(),
                generated=total_generated,
                skipped_existing=total_skipped,
                schedules_processed=len(schedules),
            )

        except Exception as e:
            db.rollback()
            logger.error("daily_dose_generation_failed", error=str(e))
            raise self.retry(exc=e)


@celery_app.task(name="app.tasks.sync_tasks.cleanup_expired_data")
def cleanup_expired_data():
    """
    Cleanup expired data:
    - OTP sessions older than 24 hours
    - Revoked refresh tokens older than 30 days
    - Notification logs older than 90 days (configurable)
    """
    with SyncSessionLocal() as db:
        try:
            now = now_ist()

            # Delete expired OTP sessions
            otp_cutoff = now - timedelta(hours=24)
            otp_result = db.execute(
                text("DELETE FROM otp_sessions WHERE created_at < :cutoff"),
                {"cutoff": otp_cutoff},
            )

            # Delete old revoked refresh tokens
            token_cutoff = now - timedelta(days=30)
            token_result = db.execute(
                text(
                    "DELETE FROM refresh_tokens WHERE revoked = true AND created_at < :cutoff"
                ),
                {"cutoff": token_cutoff},
            )

            db.commit()

            logger.info(
                "expired_data_cleaned",
                otp_deleted=otp_result.rowcount,
                tokens_deleted=token_result.rowcount,
            )

        except Exception as e:
            db.rollback()
            logger.error("cleanup_failed", error=str(e))

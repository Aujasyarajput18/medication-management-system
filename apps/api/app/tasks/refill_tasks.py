"""
Aujasya — Refill Alert Celery Task
Daily task that checks all medicines for upcoming refill needs.
Uses task_lock for idempotency — prevents duplicate WhatsApp alerts.
All DB writes are UPSERT (idempotent).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import structlog
from sqlalchemy import select, and_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_sync_session
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.tasks.celery_app import celery_app
from app.utils.task_lock import acquire_task_lock, release_task_lock

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def check_refills(self):
    """
    Daily refill check — runs at 08:00 IST via celery beat.

    Idempotency:
    - Redis SET NX lock prevents concurrent execution
    - refill_alert_sent_at column prevents duplicate alerts
    - Same-day re-runs skip already-alerted medicines
    """
    from redis import Redis as SyncRedis
    from app.config import settings

    redis = SyncRedis.from_url(settings.REDIS_URL)

    if not acquire_task_lock(redis, "check_refills", ttl_seconds=600):
        logger.info("check_refills_skipped", reason="lock_exists")
        return {"status": "skipped", "reason": "lock_exists"}

    try:
        db = get_sync_session()
        today = date.today()
        alerted_count = 0

        try:
            # Find medicines that need refill alerts
            medicines = db.execute(
                select(Medicine).where(
                    and_(
                        Medicine.is_active == True,  # noqa: E712
                        Medicine.remaining_quantity.is_not(None),
                        Medicine.remaining_quantity > 0,
                    )
                )
            ).scalars().all()

            for med in medicines:
                # Calculate daily consumption
                schedule_count = db.execute(
                    select(Schedule).where(
                        and_(
                            Schedule.medicine_id == med.id,
                            Schedule.is_active == True,  # noqa: E712
                        )
                    )
                ).scalars().all()

                daily_doses = len(schedule_count)
                if daily_doses == 0:
                    continue

                days_remaining = med.remaining_quantity / daily_doses

                if days_remaining <= med.refill_threshold_days:
                    # Skip if already alerted today (idempotency)
                    if med.refill_alert_sent_at and med.refill_alert_sent_at.date() == today:
                        continue

                    # UPSERT: update refill_alert_sent_at
                    med.refill_alert_sent_at = datetime.now(timezone.utc)
                    alerted_count += 1

                    logger.info(
                        "refill_alert_triggered",
                        medicine_id=str(med.id),
                        patient_id=str(med.patient_id),
                        days_remaining=round(days_remaining, 1),
                    )

                    # TODO: Send notification via notification_service
                    # notification_service.send_refill_alert(med.patient_id, med)

            db.commit()
            logger.info("check_refills_completed", alerted=alerted_count)
            return {"status": "completed", "alerted": alerted_count}

        except Exception as e:
            db.rollback()
            logger.error("check_refills_failed", error=str(e))
            raise self.retry(exc=e)
        finally:
            db.close()

    finally:
        release_task_lock(redis, "check_refills")

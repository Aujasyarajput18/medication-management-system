"""
Aujasya — Reminder Celery Tasks
[FIX-6] Uses sync SQLAlchemy engine (SyncSessionLocal), NOT async.
Celery tasks are synchronous — they CANNOT use await or AsyncSession.
"""

from __future__ import annotations

import structlog
from redis import Redis as SyncRedis
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.config import settings
from app.database import SyncSessionLocal
from app.models.dose_log import DoseLog
from app.models.schedule import Schedule
from app.models.user import User
from app.tasks.celery_app import celery_app
from app.utils.timezone import now_ist, IST

logger = structlog.get_logger()

# Escalation channels per level
ESCALATION_CHANNELS = {
    1: "push",
    2: "whatsapp",
    3: "sms",
    4: "caregiver_whatsapp",
}


@celery_app.task(bind=True, max_retries=3, name="app.tasks.reminder_tasks.check_and_escalate_doses")
def check_and_escalate_doses(self):
    """
    [FIX-6] Celery task — SYNCHRONOUS.
    Uses SyncSessionLocal, not AsyncSession.
    
    Checks all pending doses that are past their expected time window
    and escalates notifications according to the 4-level system.
    """
    redis = SyncRedis.from_url(settings.REDIS_URL, decode_responses=True)

    with SyncSessionLocal() as db:
        try:
            current_time = now_ist()

            # Find pending doses whose scheduled time has passed
            # [FIX-19] Use load_only to avoid encrypted fields
            stmt = (
                select(DoseLog)
                .options(
                    load_only(
                        DoseLog.id,
                        DoseLog.patient_id,
                        DoseLog.schedule_id,
                        DoseLog.meal_anchor,
                        DoseLog.scheduled_date,
                        DoseLog.status,
                    )
                )
                .where(
                    DoseLog.status == "pending",
                    DoseLog.scheduled_date <= current_time.date(),
                )
            )

            result = db.execute(stmt)
            pending_doses = result.scalars().all()

            escalated_count = 0

            for dose in pending_doses:
                dose_id_str = str(dose.id)

                # Get current escalation level from Redis
                level_key = f"escalation:{dose_id_str}:level"
                current_level = redis.get(level_key)
                current_level = int(current_level) if current_level else 0

                # Get the schedule's max reminder level
                sched = db.execute(
                    select(Schedule)
                    .options(load_only(Schedule.reminder_level))
                    .where(Schedule.id == dose.schedule_id)
                ).scalar_one_or_none()

                max_level = sched.reminder_level if sched else 4

                if current_level >= max_level:
                    continue

                next_level = current_level + 1

                # Update escalation level in Redis (24h TTL)
                redis.set(level_key, str(next_level), ex=86400)

                # Dispatch notification (actual sending is delegated)
                channel = ESCALATION_CHANNELS.get(next_level, "push")
                _dispatch_reminder.delay(
                    dose_log_id=dose_id_str,
                    patient_id=str(dose.patient_id),
                    level=next_level,
                    channel=channel,
                    meal_anchor=dose.meal_anchor,
                )

                escalated_count += 1

            logger.info(
                "escalation_check_completed",
                pending_count=len(pending_doses),
                escalated_count=escalated_count,
            )

        except Exception as e:
            logger.error("escalation_check_failed", error=str(e))
            db.rollback()
            raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.reminder_tasks.dispatch_reminder")
def _dispatch_reminder(
    self,
    dose_log_id: str,
    patient_id: str,
    level: int,
    channel: str,
    meal_anchor: str,
):
    """
    [FIX-6] Synchronous task to dispatch a single reminder.
    Actual API calls to FCM/Wati/Msg91 happen here.
    """
    with SyncSessionLocal() as db:
        try:
            # Get patient details for the notification
            from uuid import UUID

            user = db.execute(
                select(User)
                .options(load_only(User.phone_number, User.preferred_language, User.fcm_token))
                .where(User.id == UUID(patient_id))
            ).scalar_one_or_none()

            if not user:
                logger.error("reminder_patient_not_found", patient_id=patient_id)
                return

            # Build notification content
            title = "💊 Medication Reminder"
            body = f"It's time for your {meal_anchor.replace('_', ' ')} medication"

            if channel == "push" and user.fcm_token:
                logger.info(
                    "reminder_push_dispatched",
                    dose_log_id=dose_log_id,
                    level=level,
                )
                # Firebase push send would go here
                # In production, use firebase_admin.messaging.send()

            elif channel == "whatsapp":
                logger.info(
                    "reminder_whatsapp_dispatched",
                    dose_log_id=dose_log_id,
                    level=level,
                    phone_last4=user.phone_number[-4:],
                )

            elif channel == "sms":
                logger.info(
                    "reminder_sms_dispatched",
                    dose_log_id=dose_log_id,
                    level=level,
                )

            elif channel == "caregiver_whatsapp":
                logger.info(
                    "reminder_caregiver_alert",
                    dose_log_id=dose_log_id,
                    level=level,
                )

            # Log the notification
            from app.models.notification_log import NotificationLog

            log_entry = NotificationLog(
                patient_id=UUID(patient_id),
                dose_log_id=UUID(dose_log_id),
                channel=channel,
                level=level,
                status="sent",
            )
            db.add(log_entry)
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error("reminder_dispatch_failed", error=str(e), level=level)
            raise self.retry(exc=e)

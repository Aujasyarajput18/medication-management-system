"""
Aujasya — Celery Application Configuration
[FIX-5] CELERY_TIMEZONE = 'Asia/Kolkata' — NOT UTC.
All crontab schedules fire in IST.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery("aujasya")

celery_app.conf.update(
    # [FIX-5] — IST timezone for beat scheduling
    # crontab(hour=0, minute=1) will fire at 00:01 IST (18:31 UTC)
    timezone="Asia/Kolkata",
    enable_utc=True,  # Store internally as UTC, convert for scheduling

    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,

    # Limits
    task_soft_time_limit=300,   # 5 min soft limit
    task_time_limit=600,         # 10 min hard limit

    # Retry
    task_default_retry_delay=60,
    task_max_retries=3,
)

# ── Beat Schedule ────────────────────────────────────────────────────────────
# All times are in Asia/Kolkata (IST) due to timezone config above
celery_app.conf.beat_schedule = {
    # Generate daily dose logs at midnight IST
    "generate-daily-doses": {
        "task": "app.tasks.sync_tasks.generate_daily_doses",
        "schedule": crontab(hour=0, minute=1),  # [FIX-5] 00:01 IST
        "options": {"queue": "default"},
    },
    # Check for overdue doses and escalate every 5 minutes
    "check-escalation": {
        "task": "app.tasks.reminder_tasks.check_and_escalate_doses",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "options": {"queue": "reminders"},
    },
    # Clean up expired OTP sessions daily
    "cleanup-expired-otps": {
        "task": "app.tasks.sync_tasks.cleanup_expired_data",
        "schedule": crontab(hour=2, minute=0),  # 02:00 IST
        "options": {"queue": "maintenance"},
    },

    # ── Phase 2 Beat Schedules ───────────────────────────────────────────

    # Check for medicines needing refill — daily at 08:00 IST
    "check-refills": {
        "task": "app.tasks.refill_tasks.check_refills",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "maintenance"},
    },
    # Purge expired drug interaction cache entries — weekly Sunday 02:00 IST
    "refresh-interaction-cache": {
        "task": "app.tasks.interaction_cache_tasks.refresh_interaction_cache",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "options": {"queue": "maintenance"},
    },
    # Purge expired generic search cache — weekly Sunday 02:30 IST
    "cleanup-generic-cache": {
        "task": "app.tasks.interaction_cache_tasks.cleanup_generic_cache",
        "schedule": crontab(hour=2, minute=30, day_of_week=0),
        "options": {"queue": "maintenance"},
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])

"""
Aujasya — Interaction Cache Maintenance Celery Task
Weekly task that refreshes expired drug_interaction_cache entries.
Uses task_lock for idempotency. All writes are UPSERT.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, delete, and_

from app.database import get_sync_session
from app.models.drug_interaction_cache import DrugInteractionCache
from app.tasks.celery_app import celery_app
from app.utils.task_lock import acquire_task_lock, release_task_lock

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def refresh_interaction_cache(self):
    """
    Weekly interaction cache maintenance — runs at 02:00 IST Sundays.

    Idempotency:
    - Redis SET NX lock prevents concurrent execution
    - Only deletes entries already past their TTL
    - Re-runs are safe (delete of non-existent rows is a no-op)
    """
    from redis import Redis as SyncRedis
    from app.config import settings

    redis = SyncRedis.from_url(settings.REDIS_URL)

    if not acquire_task_lock(redis, "refresh_interaction_cache", ttl_seconds=600):
        logger.info("refresh_interaction_cache_skipped", reason="lock_exists")
        return {"status": "skipped", "reason": "lock_exists"}

    try:
        db = get_sync_session()
        now = datetime.now(timezone.utc)

        try:
            # Delete expired cache entries (idempotent — deleting nothing is fine)
            result = db.execute(
                delete(DrugInteractionCache).where(
                    DrugInteractionCache.expires_at < now
                )
            )
            expired_count = result.rowcount

            db.commit()
            logger.info(
                "interaction_cache_refreshed",
                expired_deleted=expired_count,
            )
            return {"status": "completed", "expired_deleted": expired_count}

        except Exception as e:
            db.rollback()
            logger.error("interaction_cache_refresh_failed", error=str(e))
            raise self.retry(exc=e)
        finally:
            db.close()

    finally:
        release_task_lock(redis, "refresh_interaction_cache")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_generic_cache(self):
    """
    Weekly cleanup of expired generic_search_cache entries.
    Same idempotency pattern as interaction cache.
    """
    from redis import Redis as SyncRedis
    from app.config import settings
    from app.models.generic_search_cache import GenericSearchCache

    redis = SyncRedis.from_url(settings.REDIS_URL)

    if not acquire_task_lock(redis, "cleanup_generic_cache", ttl_seconds=300):
        return {"status": "skipped"}

    try:
        db = get_sync_session()
        now = datetime.now(timezone.utc)

        try:
            result = db.execute(
                delete(GenericSearchCache).where(
                    GenericSearchCache.expires_at < now
                )
            )
            db.commit()
            return {"status": "completed", "deleted": result.rowcount}
        except Exception as e:
            db.rollback()
            raise self.retry(exc=e)
        finally:
            db.close()

    finally:
        release_task_lock(redis, "cleanup_generic_cache")

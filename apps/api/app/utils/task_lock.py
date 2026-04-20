"""
Aujasya — Celery Task Idempotency Guard

Prevents duplicate task execution when a worker crashes mid-run and the task
retries. Uses Redis SET NX (atomic) with a TTL to ensure only one instance
of a periodic task runs at a time.

Usage in a Celery task:
    @celery_app.task(bind=True, max_retries=2)
    def my_periodic_task(self):
        redis = get_sync_redis()
        if not acquire_task_lock(redis, 'my_periodic_task', ttl_seconds=600):
            logger.info("task_already_running", task="my_periodic_task")
            return
        try:
            # ... task logic (all DB writes must be idempotent / upsert) ...
        finally:
            release_task_lock(redis, 'my_periodic_task')
"""

from __future__ import annotations

import structlog
from redis import Redis as SyncRedis

logger = structlog.get_logger()


def acquire_task_lock(
    redis: SyncRedis,
    task_name: str,
    ttl_seconds: int = 300,
) -> bool:
    """
    Acquire a distributed lock for a Celery task.

    Uses Redis SET NX (set-if-not-exists) for atomicity.
    TTL ensures the lock is released even if the worker crashes
    without running the finally block.

    Args:
        redis: Synchronous Redis client (Celery tasks are sync).
        task_name: Unique identifier for the task.
        ttl_seconds: Lock TTL. Set to > expected task duration.
                     Default 300s (5 min). Refill check: use 600s.

    Returns:
        True if lock acquired (proceed with task).
        False if another worker already holds the lock (skip).
    """
    lock_key = f"task_lock:{task_name}"
    acquired = redis.set(lock_key, "1", nx=True, ex=ttl_seconds)

    if acquired:
        logger.info("task_lock_acquired", task=task_name, ttl=ttl_seconds)
    else:
        logger.info("task_lock_exists", task=task_name)

    return bool(acquired)


def release_task_lock(redis: SyncRedis, task_name: str) -> None:
    """
    Release the distributed lock for a Celery task.

    Called in the finally block to ensure cleanup.
    Safe to call even if the lock was never acquired or already expired.
    """
    lock_key = f"task_lock:{task_name}"
    deleted = redis.delete(lock_key)

    if deleted:
        logger.info("task_lock_released", task=task_name)

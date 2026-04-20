"""
Aujasya — Task Lock Idempotency Unit Tests
Verifies that Redis SET NX locks prevent duplicate task execution.
"""
import pytest
import pytest_asyncio
from redis import Redis as SyncRedis

from app.utils.task_lock import acquire_task_lock, release_task_lock


@pytest.fixture
def sync_redis():
    redis = SyncRedis.from_url("redis://localhost:6379/15", decode_responses=True)
    redis.flushdb()
    yield redis
    redis.flushdb()
    redis.close()


def test_acquire_lock_succeeds(sync_redis):
    result = acquire_task_lock(sync_redis, "test_task", ttl_seconds=10)
    assert result is True


def test_acquire_lock_fails_if_already_held(sync_redis):
    # First acquisition succeeds
    assert acquire_task_lock(sync_redis, "test_task", ttl_seconds=10) is True

    # Second acquisition fails (lock held)
    assert acquire_task_lock(sync_redis, "test_task", ttl_seconds=10) is False


def test_release_lock_allows_reacquisition(sync_redis):
    acquire_task_lock(sync_redis, "test_task", ttl_seconds=10)
    release_task_lock(sync_redis, "test_task")

    # Can acquire again after release
    assert acquire_task_lock(sync_redis, "test_task", ttl_seconds=10) is True


def test_different_tasks_independent(sync_redis):
    assert acquire_task_lock(sync_redis, "task_a", ttl_seconds=10) is True
    assert acquire_task_lock(sync_redis, "task_b", ttl_seconds=10) is True

    # Both should be locked
    assert acquire_task_lock(sync_redis, "task_a", ttl_seconds=10) is False
    assert acquire_task_lock(sync_redis, "task_b", ttl_seconds=10) is False


def test_lock_key_format(sync_redis):
    acquire_task_lock(sync_redis, "check_refills", ttl_seconds=10)
    assert sync_redis.exists("task_lock:check_refills") == 1


def test_lock_has_ttl(sync_redis):
    acquire_task_lock(sync_redis, "test_task", ttl_seconds=10)
    ttl = sync_redis.ttl("task_lock:test_task")
    assert 0 < ttl <= 10

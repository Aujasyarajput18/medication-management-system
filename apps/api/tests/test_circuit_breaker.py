"""
Aujasya — Circuit Breaker Unit Tests
Tests the 3-state circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis

from app.utils.circuit_breaker import CircuitBreaker, CircuitState


@pytest_asyncio.fixture
async def test_redis():
    redis = Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await redis.flushdb()
    yield redis
    await redis.flushdb()
    await redis.close()


@pytest.mark.asyncio
async def test_circuit_starts_closed(test_redis):
    cb = CircuitBreaker("test_service", test_redis)
    state = await cb.get_state()
    assert state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold(test_redis):
    cb = CircuitBreaker("test_service", test_redis, failure_threshold=3)

    # Record 3 failures
    for _ in range(3):
        await cb.record_failure()

    state = await cb.get_state()
    assert state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_allows_request_when_closed(test_redis):
    cb = CircuitBreaker("test_service", test_redis)
    assert await cb.allow_request() is True


@pytest.mark.asyncio
async def test_circuit_blocks_request_when_open(test_redis):
    cb = CircuitBreaker("test_service", test_redis, failure_threshold=2)

    await cb.record_failure()
    await cb.record_failure()

    assert await cb.allow_request() is False


@pytest.mark.asyncio
async def test_circuit_resets_on_success(test_redis):
    cb = CircuitBreaker("test_service", test_redis, failure_threshold=3)

    # Record 2 failures (below threshold)
    await cb.record_failure()
    await cb.record_failure()
    assert await cb.get_state() == CircuitState.CLOSED

    # Success resets counter
    await cb.record_success()

    # Record 2 more failures — should still be closed (counter was reset)
    await cb.record_failure()
    await cb.record_failure()
    assert await cb.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_failure_count_increments(test_redis):
    cb = CircuitBreaker("test_service", test_redis, failure_threshold=5)

    await cb.record_failure()
    await cb.record_failure()

    failures = await test_redis.get("circuit:test_service:failures")
    assert int(failures) == 2

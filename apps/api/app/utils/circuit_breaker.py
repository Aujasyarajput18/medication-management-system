"""
Aujasya — Circuit Breaker for External API Resilience

3-state circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED
State and failure counts stored in Redis for shared state across workers.

Usage:
    breaker = CircuitBreaker(redis, "bhashini")
    if await breaker.is_open():
        return fallback_response()  # Don't even try
    try:
        result = await call_bhashini_api(...)
        await breaker.record_success()
        return result
    except ExternalAPIError:
        await breaker.record_failure()
        return fallback_response()
"""

from __future__ import annotations

from enum import Enum

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation — requests flow through
    OPEN = "open"            # Failures exceeded threshold — requests blocked
    HALF_OPEN = "half_open"  # Testing recovery — one request allowed through


# Default thresholds — can be overridden per service
DEFAULT_FAILURE_THRESHOLD = 5       # Consecutive failures before opening
DEFAULT_RECOVERY_TIMEOUT_S = 60     # Seconds before trying half-open
DEFAULT_SUCCESS_THRESHOLD = 2       # Successes in half-open before closing


class CircuitBreaker:
    """
    Redis-backed circuit breaker for external API calls.

    Keys used in Redis:
        circuit:{service}:state     — current state (closed/open/half_open)
        circuit:{service}:failures  — consecutive failure count
        circuit:{service}:opened_at — timestamp when circuit opened (TTL-based recovery)
        circuit:{service}:half_open_successes — successes during half-open
    """

    def __init__(
        self,
        redis: Redis,
        service_name: str,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout_s: int = DEFAULT_RECOVERY_TIMEOUT_S,
        success_threshold: int = DEFAULT_SUCCESS_THRESHOLD,
    ) -> None:
        self.redis = redis
        self.service = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.success_threshold = success_threshold
        self._prefix = f"circuit:{service_name}"

    async def get_state(self) -> CircuitState:
        """Get the current circuit state."""
        state = await self.redis.get(f"{self._prefix}:state")
        if state is None:
            return CircuitState.CLOSED
        return CircuitState(state)

    async def is_open(self) -> bool:
        """
        Check if circuit is open (should block requests).

        If the circuit is OPEN and recovery_timeout has elapsed,
        automatically transition to HALF_OPEN.
        """
        state = await self.get_state()

        if state == CircuitState.CLOSED:
            return False

        if state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            opened_at_exists = await self.redis.exists(
                f"{self._prefix}:opened_at"
            )
            if not opened_at_exists:
                # TTL expired — transition to half-open
                await self._set_state(CircuitState.HALF_OPEN)
                logger.info(
                    "circuit_half_open",
                    service=self.service,
                )
                return False  # Allow one request through
            return True  # Still within recovery timeout

        # HALF_OPEN — allow requests through (testing recovery)
        return False

    async def record_success(self) -> None:
        """Record a successful external API call."""
        state = await self.get_state()

        if state == CircuitState.HALF_OPEN:
            successes = await self.redis.incr(
                f"{self._prefix}:half_open_successes"
            )
            if successes >= self.success_threshold:
                await self._reset()
                logger.info(
                    "circuit_closed",
                    service=self.service,
                    reason="recovery_successful",
                )
        elif state == CircuitState.CLOSED:
            # Reset failure count on success
            await self.redis.delete(f"{self._prefix}:failures")

    async def record_failure(self) -> None:
        """Record a failed external API call."""
        state = await self.get_state()

        if state == CircuitState.HALF_OPEN:
            # Single failure in half-open → back to open
            await self._open_circuit()
            logger.warning(
                "circuit_reopened",
                service=self.service,
                reason="half_open_failure",
            )
            return

        # CLOSED state — increment failure count
        failures = await self.redis.incr(f"{self._prefix}:failures")

        if failures >= self.failure_threshold:
            await self._open_circuit()
            logger.warning(
                "circuit_opened",
                service=self.service,
                failures=failures,
                recovery_timeout_s=self.recovery_timeout_s,
            )

    async def _open_circuit(self) -> None:
        """Transition to OPEN state."""
        await self._set_state(CircuitState.OPEN)
        # Set a key with TTL for recovery timeout
        await self.redis.set(
            f"{self._prefix}:opened_at",
            "1",
            ex=self.recovery_timeout_s,
        )
        # Reset half-open successes
        await self.redis.delete(f"{self._prefix}:half_open_successes")

    async def _set_state(self, state: CircuitState) -> None:
        """Set the circuit state in Redis. 1-hour TTL for auto-cleanup."""
        await self.redis.set(
            f"{self._prefix}:state",
            state.value,
            ex=3600,
        )

    async def _reset(self) -> None:
        """Reset circuit to CLOSED — clear all tracking keys."""
        keys = [
            f"{self._prefix}:state",
            f"{self._prefix}:failures",
            f"{self._prefix}:opened_at",
            f"{self._prefix}:half_open_successes",
        ]
        await self.redis.delete(*keys)


# ── Pre-configured service fallback contracts ─────────────────────────────
# Document what each service degrades to when its circuit is OPEN.
# Used by service layers to decide fallback behavior.

SERVICE_FALLBACKS: dict[str, str] = {
    "bhashini": "Return service_unavailable; frontend falls back to text input",
    "ekacare": "Return from generic_search_cache (stale data acceptable)",
    "pmbjp": "Show last-known Jan Aushadhi locations from cache",
    "aladhan": "Try SunriseSunset API → static 50-city JSON fallback",
    "exotel": "Skip IVR; escalate via WhatsApp instead",
    "rxnorm": "Return from drug_interaction_cache (stale data acceptable)",
    "openfda": "Return from drug_interaction_cache (stale data acceptable)",
}

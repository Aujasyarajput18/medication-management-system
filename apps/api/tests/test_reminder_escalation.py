"""
Aujasya — Reminder Escalation Tests
Tests 4-level escalation, idempotency, cancellation.
[FIX-5] Verifies IST timezone, [FIX-6] verifies sync engine compatibility.
"""

from __future__ import annotations

import uuid

import pytest
from redis.asyncio import Redis

from app.services.reminder_service import ReminderService


class TestEscalationStateMachine:
    """Test the 4-level escalation state machine."""

    @pytest.mark.asyncio
    async def test_initial_level_is_zero(self, test_redis: Redis):
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()
        level = await service.get_escalation_level(dose_id)
        assert level == 0

    @pytest.mark.asyncio
    async def test_escalation_increments(self, test_redis: Redis):
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()

        # Level 1
        should_send, next_level = await service.should_escalate(dose_id)
        assert should_send is True
        assert next_level == 1
        await service.set_escalation_level(dose_id, next_level)

        # Level 2
        should_send, next_level = await service.should_escalate(dose_id)
        assert should_send is True
        assert next_level == 2

    @pytest.mark.asyncio
    async def test_max_level_stops_escalation(self, test_redis: Redis):
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()

        # Set to max level (4)
        await service.set_escalation_level(dose_id, 4)

        should_send, level = await service.should_escalate(dose_id, max_level=4)
        assert should_send is False

    @pytest.mark.asyncio
    async def test_cancellation_prevents_escalation(self, test_redis: Redis):
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()

        await service.set_escalation_level(dose_id, 2)
        await service.cancel_escalation(dose_id)

        # After cancellation, level resets to 0
        level = await service.get_escalation_level(dose_id)
        assert level == 0

    @pytest.mark.asyncio
    async def test_escalate_returns_channel_info(self, test_redis: Redis):
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()
        patient_id = uuid.uuid4()

        result = await service.escalate(dose_id, patient_id)
        assert result is not None
        assert result["level"] == 1
        assert result["channel"] == "push"

    @pytest.mark.asyncio
    async def test_idempotent_level_check(self, test_redis: Redis):
        """Same level should not trigger re-send."""
        service = ReminderService(test_redis)
        dose_id = uuid.uuid4()

        await service.set_escalation_level(dose_id, 2)

        # should_escalate checks for next level (3), not re-send current (2)
        should_send, next_level = await service.should_escalate(dose_id)
        assert should_send is True
        assert next_level == 3  # Moves to next, doesn't repeat 2


class TestCeleryTimezone:
    """[FIX-5] Verify Celery timezone configuration."""

    def test_celery_timezone_is_ist(self):
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.timezone == "Asia/Kolkata"

    def test_celery_utc_enabled(self):
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.enable_utc is True


class TestSyncEngine:
    """[FIX-6] Verify sync engine is available for Celery tasks."""

    def test_sync_session_importable(self):
        from app.database import SyncSessionLocal, sync_engine

        assert SyncSessionLocal is not None
        assert sync_engine is not None

    def test_sync_url_uses_psycopg2(self):
        from app.config import settings

        sync_url = settings.sync_database_url
        assert "+psycopg2" in sync_url
        assert "+asyncpg" not in sync_url

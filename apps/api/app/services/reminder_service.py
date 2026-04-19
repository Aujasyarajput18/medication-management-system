"""
Aujasya — Reminder Service
4-level escalation state machine for missed doses.
L1: Push notification (at dose time)
L2: WhatsApp message (+30 min)
L3: SMS to patient (+60 min)
L4: Caregiver WhatsApp alert (+90 min)
"""

from __future__ import annotations

import uuid

import structlog
from redis.asyncio import Redis

from app.models.dose_log import DoseLog

logger = structlog.get_logger()

# Escalation levels and their delays (minutes from dose time)
ESCALATION_LEVELS = {
    1: {"delay_minutes": 0, "channel": "push", "description": "Push notification"},
    2: {"delay_minutes": 30, "channel": "whatsapp", "description": "WhatsApp to patient"},
    3: {"delay_minutes": 60, "channel": "sms", "description": "SMS to patient"},
    4: {"delay_minutes": 90, "channel": "caregiver_whatsapp", "description": "WhatsApp to caregivers"},
}


class ReminderService:
    """
    Manages the 4-level escalation state machine.
    Uses Redis keys for idempotency and level tracking:
    - escalation:{dose_log_id}:level = current escalation level
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get_escalation_level(self, dose_log_id: uuid.UUID) -> int:
        """Get current escalation level for a dose (0 = not started)."""
        level = await self.redis.get(f"escalation:{dose_log_id}:level")
        return int(level) if level else 0

    async def set_escalation_level(
        self, dose_log_id: uuid.UUID, level: int
    ) -> None:
        """Set escalation level. TTL = 24 hours (auto-cleanup)."""
        await self.redis.set(
            f"escalation:{dose_log_id}:level",
            str(level),
            ex=86400,  # 24 hour TTL
        )

    async def cancel_escalation(self, dose_log_id: uuid.UUID) -> None:
        """Cancel escalation when dose is taken or skipped."""
        await self.redis.delete(f"escalation:{dose_log_id}:level")
        logger.info("escalation_cancelled", dose_log_id=str(dose_log_id))

    async def should_escalate(
        self,
        dose_log_id: uuid.UUID,
        max_level: int = 4,
    ) -> tuple[bool, int]:
        """
        Check if escalation should proceed.
        Returns (should_send, next_level).
        Idempotent: same level won't re-send.
        """
        current_level = await self.get_escalation_level(dose_log_id)
        next_level = current_level + 1

        if next_level > max_level:
            return False, current_level

        return True, next_level

    async def escalate(
        self,
        dose_log_id: uuid.UUID,
        patient_id: uuid.UUID,
        max_level: int = 4,
    ) -> dict | None:
        """
        Execute next escalation level.
        Returns the notification details or None if max level reached.
        """
        should_send, next_level = await self.should_escalate(dose_log_id, max_level)

        if not should_send:
            logger.info(
                "escalation_max_reached",
                dose_log_id=str(dose_log_id),
            )
            return None

        level_config = ESCALATION_LEVELS.get(next_level)
        if not level_config:
            return None

        # Update level
        await self.set_escalation_level(dose_log_id, next_level)

        logger.info(
            "escalation_triggered",
            dose_log_id=str(dose_log_id),
            level=next_level,
            channel=level_config["channel"],
        )

        return {
            "dose_log_id": str(dose_log_id),
            "patient_id": str(patient_id),
            "level": next_level,
            "channel": level_config["channel"],
            "description": level_config["description"],
        }

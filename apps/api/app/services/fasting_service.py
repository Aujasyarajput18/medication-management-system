"""
Aujasya — Fasting Service
Clinical rescheduling rules with NEVER_AUTO_RESCHEDULE safety guard.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_decision_log import AiDecisionLog
from app.models.fasting_profile import FastingProfile, FastingScheduleOverride
from app.models.medicine import Medicine
from app.models.schedule import Schedule

logger = structlog.get_logger()

# ── CRITICAL SAFETY GUARD ────────────────────────────────────────────────────
# These drug classes must NEVER be auto-rescheduled during fasting.
# Any match triggers a CRITICAL warning and blocks the adjustment.
NEVER_AUTO_RESCHEDULE = frozenset([
    # Insulin — risk of hypoglycemia
    "insulin", "insulin glargine", "insulin aspart", "insulin lispro",
    "insulin detemir", "insulin degludec", "insulin regular",
    # Anticoagulants — narrow therapeutic index
    "warfarin", "acenocoumarol", "dabigatran", "rivaroxaban", "apixaban",
    # Immunosuppressants — strict dosing schedule
    "tacrolimus", "cyclosporine", "mycophenolate", "azathioprine",
    # Narrow therapeutic index drugs
    "phenytoin", "carbamazepine", "valproate", "valproic acid",
    "lithium", "digoxin", "theophylline", "aminophylline",
    # Anti-epileptics
    "levetiracetam", "lamotrigine",
])

# Fasting meal anchor rescheduling rules
FASTING_RULES = {
    "ramadan": {
        "before_breakfast": "before_suhoor",
        "with_breakfast": "with_suhoor",
        "after_breakfast": "after_suhoor",
        "before_lunch": "skip",       # No lunch during Ramadan fast
        "with_lunch": "skip",
        "after_lunch": "skip",
        "before_dinner": "before_iftar",
        "with_dinner": "with_iftar",
        "after_dinner": "after_iftar",
        "bedtime": "bedtime",          # Usually unchanged
    },
    "navratri": {
        "before_lunch": "before_dinner",
        "with_lunch": "with_dinner",
        "after_lunch": "after_dinner",
    },
}


class FastingService:
    """Fasting mode activation with clinical safety guards."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def activate_fasting(
        self,
        patient_id: uuid.UUID,
        fasting_type: str,
        start_date,
        end_date,
        lat: float,
        lng: float,
    ) -> dict:
        """Activate fasting mode for a patient. Returns adjustments and blocked meds."""

        # Get patient's active schedules with medicines
        stmt = (
            select(Schedule, Medicine)
            .join(Medicine, Schedule.medicine_id == Medicine.id)
            .where(
                Schedule.patient_id == patient_id,
                Schedule.is_active == True,  # noqa: E712
                Medicine.is_active == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        schedule_medicine_pairs = result.all()

        rules = FASTING_RULES.get(fasting_type, FASTING_RULES.get("ramadan", {}))
        adjustments = []
        blocked = []

        for schedule, medicine in schedule_medicine_pairs:
            active_ingredient = (medicine.active_ingredient or "").strip().lower()

            # ── SAFETY CHECK: NEVER_AUTO_RESCHEDULE ──────────────────
            is_blocked = any(
                drug in active_ingredient
                for drug in NEVER_AUTO_RESCHEDULE
            )

            if is_blocked:
                blocked.append({
                    "schedule_id": str(schedule.id),
                    "medicine_name": medicine.brand_name,
                    "original_meal_anchor": schedule.meal_anchor,
                    "adjusted_meal_anchor": schedule.meal_anchor,  # No change
                    "reason": f"CRITICAL: {medicine.brand_name} contains {active_ingredient} — "
                              f"cannot be auto-rescheduled. Contact your doctor.",
                    "severity_level": "critical",
                    "physician_note_required": True,
                    "blocked": True,
                })

                # Log blocked decision
                await self._log_decision(
                    patient_id, "fasting_reschedule", medicine.brand_name,
                    {"blocked": True, "reason": "NEVER_AUTO_RESCHEDULE"}, "blocked",
                )
                continue

            # ── Normal rescheduling ──────────────────────────────────
            adjusted = rules.get(schedule.meal_anchor, schedule.meal_anchor)

            if adjusted == "skip":
                adjustments.append({
                    "schedule_id": str(schedule.id),
                    "medicine_name": medicine.brand_name,
                    "original_meal_anchor": schedule.meal_anchor,
                    "adjusted_meal_anchor": "skipped_during_fast",
                    "reason": f"No equivalent meal anchor during {fasting_type} fast",
                    "severity_level": "warning",
                    "blocked": False,
                })
            elif adjusted != schedule.meal_anchor:
                adjustments.append({
                    "schedule_id": str(schedule.id),
                    "medicine_name": medicine.brand_name,
                    "original_meal_anchor": schedule.meal_anchor,
                    "adjusted_meal_anchor": adjusted,
                    "reason": f"Shifted from {schedule.meal_anchor} to {adjusted} for {fasting_type}",
                    "severity_level": "info",
                    "blocked": False,
                })

                await self._log_decision(
                    patient_id, "fasting_reschedule", medicine.brand_name,
                    {"from": schedule.meal_anchor, "to": adjusted}, "accepted",
                )

        # Create fasting profile
        profile = FastingProfile(
            patient_id=patient_id,
            fasting_type=fasting_type,
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
            disclaimer_accepted=True,
            disclaimer_accepted_at=datetime.now(timezone.utc),
        )
        self.db.add(profile)
        await self.db.flush()

        # Create schedule overrides
        for adj in adjustments:
            if adj.get("adjusted_meal_anchor") != "skipped_during_fast":
                override = FastingScheduleOverride(
                    fasting_profile_id=profile.id,
                    schedule_id=uuid.UUID(adj["schedule_id"]),
                    original_meal_anchor=adj["original_meal_anchor"],
                    adjusted_meal_anchor=adj["adjusted_meal_anchor"],
                    adjustment_reason=adj["reason"],
                )
                self.db.add(override)

        return {
            "fasting_profile_id": str(profile.id),
            "fasting_type": fasting_type,
            "adjustments": adjustments,
            "blocked_medications": blocked,
            "pharmacist_reviewed": False,
        }

    async def _log_decision(
        self, patient_id, decision_type, medicine_name, details, action,
    ) -> None:
        log = AiDecisionLog(
            patient_id=patient_id,
            decision_type=decision_type,
            input_summary=f"Fasting reschedule: {medicine_name}",
            output_summary=details,
            user_action=action,
        )
        self.db.add(log)
        await self.db.flush()

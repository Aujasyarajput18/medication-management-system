"""
Aujasya — Caregiver Service
[FIX-18] Pre-assigns role='caregiver' when creating pending user records.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caregiver_link import CaregiverLink
from app.models.user import User
from app.schemas.caregiver import (
    CaregiverLinkResponse,
    InviteRequest,
    PatientSummaryResponse,
)
from app.services.dose_service import DoseService
from app.services.encryption_service import encryption_service
from app.utils.timezone import now_ist
from app.utils.validators import validate_indian_phone

logger = structlog.get_logger()


class CaregiverService:
    """Handles caregiver invitations, linking, and patient summaries."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def invite_caregiver(
        self, patient_id: uuid.UUID, data: InviteRequest
    ) -> CaregiverLinkResponse:
        """
        Invite a caregiver by phone number.
        [FIX-18] If no account exists, create a pending user with role='caregiver'.
        """
        if not validate_indian_phone(data.caregiver_phone):
            raise ValueError("Invalid caregiver phone number")

        # Check for self-invite
        patient_stmt = select(User).where(User.id == patient_id)
        patient_result = await self.db.execute(patient_stmt)
        patient = patient_result.scalar_one_or_none()
        if patient and patient.phone_number == data.caregiver_phone:
            raise ValueError("You cannot invite yourself as a caregiver")

        # Find or create caregiver user
        caregiver_stmt = select(User).where(User.phone_number == data.caregiver_phone)
        caregiver_result = await self.db.execute(caregiver_stmt)
        caregiver = caregiver_result.scalar_one_or_none()

        if caregiver is None:
            # [FIX-18] Create pending user with role='caregiver' pre-assigned
            # When this user later logs in via OTP, verify_otp returns
            # is_new_user=true but the role is already 'caregiver'.
            # Onboarding detects the role and skips patient-specific steps.
            caregiver = User(
                phone_number=data.caregiver_phone,
                phone_verified=False,
                role="caregiver",  # [FIX-18] — pre-assigned role
                preferred_language="hi",
            )
            self.db.add(caregiver)
            await self.db.flush()

            logger.info(
                "pending_caregiver_created",
                phone_last4=data.caregiver_phone[-4:],
                role="caregiver",
                note="[FIX-18] role pre-assigned",
            )

        # Check for existing link
        existing_stmt = select(CaregiverLink).where(
            CaregiverLink.patient_id == patient_id,
            CaregiverLink.caregiver_id == caregiver.id,
        )
        existing_result = await self.db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            if existing.status == "active":
                raise ValueError("This caregiver is already linked")
            if existing.status == "pending":
                raise ValueError("An invitation is already pending")
            # If revoked, re-invite by updating status
            existing.status = "pending"
            existing.invited_at = now_ist()
            existing.revoked_at = None
            await self.db.flush()
            return CaregiverLinkResponse.model_validate(existing)

        # Create new link
        link = CaregiverLink(
            patient_id=patient_id,
            caregiver_id=caregiver.id,
            status="pending",
        )
        self.db.add(link)
        await self.db.flush()

        logger.info(
            "caregiver_invited",
            patient_id=str(patient_id),
            caregiver_id=str(caregiver.id),
        )

        return CaregiverLinkResponse.model_validate(link)

    async def accept_invite(
        self, caregiver_id: uuid.UUID, link_id: uuid.UUID
    ) -> CaregiverLinkResponse:
        """Accept a pending caregiver invitation."""
        stmt = select(CaregiverLink).where(
            CaregiverLink.id == link_id,
            CaregiverLink.caregiver_id == caregiver_id,
            CaregiverLink.status == "pending",
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            raise ValueError("Invitation not found or already accepted")

        link.status = "active"
        link.accepted_at = now_ist()
        await self.db.flush()

        logger.info("caregiver_accepted", link_id=str(link_id))

        return CaregiverLinkResponse.model_validate(link)

    async def get_patient_summaries(
        self, caregiver_id: uuid.UUID
    ) -> list[PatientSummaryResponse]:
        """Get summary data for all linked patients (for caregiver dashboard)."""
        stmt = select(CaregiverLink).where(
            CaregiverLink.caregiver_id == caregiver_id,
            CaregiverLink.status == "active",
        )
        result = await self.db.execute(stmt)
        links = result.scalars().all()

        summaries = []
        dose_service = DoseService(self.db, self.redis)

        for link in links:
            # Get patient basic info
            patient_stmt = select(User).where(User.id == link.patient_id)
            patient_result = await self.db.execute(patient_stmt)
            patient = patient_result.scalar_one_or_none()
            if not patient:
                continue

            # Get today's doses
            today_doses = await dose_service.get_today_doses(link.patient_id)
            total_today = len(today_doses)
            taken_today = sum(1 for d in today_doses if d.status == "taken")
            has_overdue = any(d.status == "pending" for d in today_doses)

            # Get streak
            streak = await dose_service.get_streak(link.patient_id)

            name = encryption_service.decrypt_bytes(patient.full_name, "full_name")

            summaries.append(
                PatientSummaryResponse(
                    patient_id=patient.id,
                    name=name,
                    adherence_today_pct=(
                        round(taken_today / total_today * 100, 1) if total_today > 0 else 0.0
                    ),
                    total_doses_today=total_today,
                    taken_doses_today=taken_today,
                    last_seen=patient.last_seen_at,
                    current_streak=streak.current_streak,
                    has_overdue=has_overdue,
                )
            )

        return summaries

    async def revoke_link(
        self, user_id: uuid.UUID, link_id: uuid.UUID
    ) -> None:
        """Revoke a caregiver link (either party can revoke)."""
        stmt = select(CaregiverLink).where(
            CaregiverLink.id == link_id,
            (CaregiverLink.patient_id == user_id) | (CaregiverLink.caregiver_id == user_id),
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            raise ValueError("Link not found")

        link.status = "revoked"
        link.revoked_at = now_ist()
        await self.db.flush()

        logger.info("caregiver_link_revoked", link_id=str(link_id), by_user=str(user_id))

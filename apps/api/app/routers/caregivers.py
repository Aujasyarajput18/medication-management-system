"""
Aujasya — Caregivers Router
4 endpoints: invite, accept, list patients, revoke link.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AnyUser, CurrentUser, DbSession, RedisClient
from app.schemas.caregiver import (
    AcceptInviteRequest,
    CaregiverLinkResponse,
    InviteRequest,
    PatientSummaryResponse,
)
from app.services.caregiver_service import CaregiverService

router = APIRouter(prefix="/caregivers", tags=["Caregivers"])


@router.post(
    "/invite",
    response_model=CaregiverLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite caregiver",
)
async def invite_caregiver(
    body: InviteRequest,
    user: CurrentUser,
    db: DbSession,
) -> CaregiverLinkResponse:
    """Invite a caregiver by phone. Creates pending user if not registered."""
    if user.role != "patient":
        raise HTTPException(403, "Only patients can invite caregivers")
    service = CaregiverService(db)
    try:
        return await service.invite_caregiver(user.id, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post(
    "/accept",
    response_model=CaregiverLinkResponse,
    summary="Accept caregiver invite",
)
async def accept_invite(
    body: AcceptInviteRequest,
    user: CurrentUser,
    db: DbSession,
) -> CaregiverLinkResponse:
    """Accept a pending caregiver invitation."""
    if user.role != "caregiver":
        raise HTTPException(403, "Only caregivers can accept invitations")
    service = CaregiverService(db)
    try:
        return await service.accept_invite(user.id, body.link_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get(
    "/patients",
    response_model=list[PatientSummaryResponse],
    summary="Get patient summaries",
)
async def get_patient_summaries(
    user: CurrentUser,
    db: DbSession,
    redis: RedisClient,
) -> list[PatientSummaryResponse]:
    """Get summary dashboard data for all linked patients."""
    if user.role != "caregiver":
        raise HTTPException(403, "Only caregivers can view patient summaries")
    service = CaregiverService(db, redis)
    return await service.get_patient_summaries(user.id)


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke caregiver link",
)
async def revoke_link(
    link_id: UUID,
    user: AnyUser,
    db: DbSession,
) -> None:
    """Revoke a caregiver link (either patient or caregiver can revoke)."""
    service = CaregiverService(db)
    try:
        await service.revoke_link(user.id, link_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

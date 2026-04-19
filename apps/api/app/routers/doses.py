"""
Aujasya — Doses Router
Endpoints: today, taken, skipped, sync-offline, calendar, streak.
[FIX-15] Calendar accepts ?month=YYYY-MM only.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession, RedisClient
from app.schemas.dose import (
    CalendarResponse,
    DoseLogResponse,
    DoseSkippedRequest,
    DoseTakenRequest,
    OfflineSyncRequest,
    OfflineSyncResponse,
    StreakResponse,
)
from app.services.dose_service import DoseService

router = APIRouter(prefix="/doses", tags=["Doses"])


@router.get("/today", response_model=list[DoseLogResponse], summary="Today's doses")
async def get_today_doses(
    user: CurrentUser,
    db: DbSession,
) -> list[DoseLogResponse]:
    """Get all dose logs for today, grouped by meal anchor."""
    service = DoseService(db)
    return await service.get_today_doses(user.id)


@router.post(
    "/{dose_id}/taken",
    response_model=DoseLogResponse,
    summary="Mark dose as taken",
)
async def mark_dose_taken(
    dose_id: UUID,
    body: DoseTakenRequest,
    user: CurrentUser,
    db: DbSession,
    redis: RedisClient,
) -> DoseLogResponse:
    """Mark a scheduled dose as taken. Cancels any pending escalation."""
    service = DoseService(db, redis)
    try:
        return await service.mark_taken(dose_id, user.id, body)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post(
    "/{dose_id}/skipped",
    response_model=DoseLogResponse,
    summary="Mark dose as skipped",
)
async def mark_dose_skipped(
    dose_id: UUID,
    body: DoseSkippedRequest,
    user: CurrentUser,
    db: DbSession,
    redis: RedisClient,
) -> DoseLogResponse:
    """Mark a dose as skipped with a reason (min 5 chars)."""
    service = DoseService(db, redis)
    try:
        return await service.mark_skipped(dose_id, user.id, body)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post(
    "/sync-offline",
    response_model=OfflineSyncResponse,
    summary="Sync offline dose logs",
)
async def sync_offline(
    body: OfflineSyncRequest,
    user: CurrentUser,
    db: DbSession,
) -> OfflineSyncResponse:
    """Batch-process offline dose mutations (last device_timestamp wins)."""
    service = DoseService(db)
    return await service.sync_offline(user.id, body)


@router.get("/calendar", response_model=CalendarResponse, summary="Calendar view")
async def get_calendar(
    user: CurrentUser,
    db: DbSession,
    month: str = Query(
        ...,
        description="Month in YYYY-MM format",
        regex=r"^\d{4}-\d{2}$",
        examples=["2025-01"],
    ),
) -> CalendarResponse:
    """
    Get calendar adherence data for a month.
    [FIX-15] Uses month=YYYY-MM only (no separate year parameter).
    """
    service = DoseService(db)
    try:
        return await service.get_calendar(user.id, month)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/streak", response_model=StreakResponse, summary="Adherence streak")
async def get_streak(
    user: CurrentUser,
    db: DbSession,
) -> StreakResponse:
    """Get current streak, longest streak, and 30-day adherence."""
    service = DoseService(db)
    return await service.get_streak(user.id)

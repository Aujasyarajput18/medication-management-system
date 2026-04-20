"""
Aujasya — Journal & Refills Router
Side-effect journal CRUD and refill tracking endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalPatternsResponse,
    RefillStatus,
    RefillCountUpdate,
)

router = APIRouter(tags=["Journal & Refills"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


# ── Journal Endpoints ────────────────────────────────────────────────────

@router.post("/journal/entry", response_model=JournalEntryResponse)
async def create_journal_entry(
    body: JournalEntryCreate,
    patient_id: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a side-effect journal entry with NLP normalization."""
    from app.services.journal_service import JournalService

    service = JournalService(db)
    entry = await service.create_entry(
        patient_id=uuid.UUID(patient_id),
        symptom_text=body.symptom_text,
        severity=body.severity,
        onset_date=body.onset_date,
        input_method=body.input_method,
        medicine_id=uuid.UUID(body.medicine_id) if body.medicine_id else None,
        dose_log_id=uuid.UUID(body.dose_log_id) if body.dose_log_id else None,
        voice_transcript=body.voice_transcript,
    )

    return JournalEntryResponse(
        id=str(entry.id),
        medicine_id=str(entry.medicine_id) if entry.medicine_id else None,
        symptom_text=entry.symptom_text,
        symptom_normalized=entry.symptom_normalized or [],
        severity=entry.severity or "",
        onset_date=entry.onset_date,
        resolved_date=entry.resolved_date,
        input_method=entry.input_method,
        is_flagged=entry.is_flagged,
        flag_reason=entry.flag_reason,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )


@router.get("/journal/patterns", response_model=JournalPatternsResponse)
async def get_patterns(
    patient_id: str = Query(...),
    period_days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_async_session),
):
    """Detect recurring side-effect patterns over a period."""
    from app.services.journal_service import JournalService

    service = JournalService(db)
    patterns = await service.get_patterns(uuid.UUID(patient_id), period_days)
    return JournalPatternsResponse(patterns=patterns, period_days=period_days)


# ── Refill Endpoints ─────────────────────────────────────────────────────

@router.get("/refills/status", response_model=list[RefillStatus])
async def get_refill_status(
    patient_id: str = Query(...),
    latitude: float = Query(None),
    longitude: float = Query(None),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    """Get refill status for all active medicines."""
    from app.services.refill_service import RefillService

    service = RefillService(db, redis)
    return await service.get_refill_status(
        patient_id=uuid.UUID(patient_id),
        lat=latitude,
        lng=longitude,
    )


@router.patch("/refills/{medicine_id}/count")
async def update_refill_count(
    medicine_id: str,
    body: RefillCountUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update remaining quantity for a medicine."""
    from app.services.refill_service import RefillService
    from redis.asyncio import Redis as AsyncRedis
    redis = AsyncRedis.from_url("redis://localhost:6379/0")

    service = RefillService(db, redis)
    await service.update_count(uuid.UUID(medicine_id), body.remaining_quantity)
    return {"updated": True}

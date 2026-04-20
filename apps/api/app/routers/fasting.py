"""Aujasya — Fasting Router"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.fasting import FastingActivateRequest, FastingActivateResponse, PrayerTimesResponse
from app.services.fasting_service import FastingService
from app.services.prayer_time_service import PrayerTimeService

router = APIRouter(prefix="/fasting", tags=["Fasting Mode"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


@router.get("/prayer-times", response_model=PrayerTimesResponse)
async def get_prayer_times(
    latitude: float = Query(...),
    longitude: float = Query(...),
    redis: Redis = Depends(get_redis),
):
    """Get suhoor/iftar times for a location. 3-level fallback."""
    service = PrayerTimeService(redis)
    result = await service.get_prayer_times(latitude, longitude)
    return PrayerTimesResponse(**result)


@router.post("/activate", response_model=FastingActivateResponse)
async def activate_fasting(
    body: FastingActivateRequest,
    patient_id: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
):
    """Activate fasting mode. Returns schedule adjustments and blocked medications."""
    service = FastingService(db)
    result = await service.activate_fasting(
        patient_id=uuid.UUID(patient_id),
        fasting_type=body.fasting_type,
        start_date=body.start_date,
        end_date=body.end_date,
        lat=body.latitude,
        lng=body.longitude,
    )
    return result

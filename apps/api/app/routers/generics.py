"""Aujasya — Generics Router"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.generic import GenericSearchResponse

router = APIRouter(prefix="/generics", tags=["Generic Discovery"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


@router.get("/search", response_model=GenericSearchResponse)
async def search_generics(
    brand_name: str = Query(..., min_length=2),
    patient_id: str = Query(...),
    latitude: float = Query(None),
    longitude: float = Query(None),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    """Search for generic alternatives to a branded medicine."""
    from app.services.generic_service import GenericService
    service = GenericService(db, redis)
    result = await service.search_alternatives(
        brand_name=brand_name,
        patient_id=uuid.UUID(patient_id),
        lat=latitude,
        lng=longitude,
    )
    return result

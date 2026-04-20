"""Aujasya — Drug Interactions Router"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.interaction import InteractionCheckRequest, InteractionCheckResponse, RxcuiLookupResponse
from app.services.interaction_service import InteractionService

router = APIRouter(prefix="/interactions", tags=["Drug Interactions"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


@router.post("/check", response_model=InteractionCheckResponse)
async def check_interactions(
    body: InteractionCheckRequest,
    patient_id: str = Query(...),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    """Check drug interactions for a list of RxCUIs. Purely informational — never blocks user."""
    service = InteractionService(db, redis)
    result = await service.check_interactions(body.rxcui_list, uuid.UUID(patient_id))
    return result


@router.get("/medicine/{medicine_name}/rxcui", response_model=RxcuiLookupResponse)
async def resolve_rxcui(
    medicine_name: str,
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    """Resolve a medicine name to its RxNorm CUI for interaction checking."""
    service = InteractionService(db, redis)
    result = await service.resolve_rxcui(medicine_name)
    if result:
        return RxcuiLookupResponse(**result)
    return RxcuiLookupResponse(found=False)

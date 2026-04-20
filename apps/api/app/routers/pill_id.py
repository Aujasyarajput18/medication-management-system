"""Aujasya — Pill ID Router"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.pill_id import PillIdResponse, PillCandidate
from app.services.pill_id_service import PillIdService

router = APIRouter(prefix="/pill-id", tags=["Pill Identification"])


@router.get("/identify", response_model=PillIdResponse)
async def identify_pill(
    patient_id: str = Query(...),
    color: str = Query(None),
    shape: str = Query(None),
    imprint: str = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """Identify a pill by appearance (color, shape, imprint)."""
    import uuid
    service = PillIdService(db)
    candidates = await service.match_by_appearance(
        patient_id=uuid.UUID(patient_id), color=color, shape=shape, imprint=imprint,
    )
    return PillIdResponse(
        candidates=[PillCandidate(**c) for c in candidates],
        model_version="appearance-v1",
        source="server_db",
    )

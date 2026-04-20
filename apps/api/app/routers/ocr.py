"""
Aujasya — OCR Router
Endpoints for prescription scanning and confirmation.
Requires 'prescription_ocr' consent.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.ocr import OcrScanResponse, OcrConfirmRequest, OcrConfirmResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/ocr", tags=["OCR"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


@router.post("/scan-prescription", response_model=OcrScanResponse)
async def scan_prescription(
    image: UploadFile = File(None),
    tesseract_text: str = Form(""),
    tesseract_confidence: float = Form(0.0),
    patient_id: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
):
    """
    Process a prescription image through the OCR pipeline.
    Client may send pre-processed Tesseract text from the WebWorker,
    or send the raw image for server-side processing.
    """
    from app.services.ocr_service import OcrService

    image_bytes = None
    if image:
        image_bytes = await image.read()
        max_size = 10 * 1024 * 1024
        if len(image_bytes) > max_size:
            raise HTTPException(413, "Image exceeds 10MB limit")

    service = OcrService(db, redis)
    result = await service.process_prescription(
        patient_id=uuid.UUID(patient_id),
        image_bytes=image_bytes,
        tesseract_text=tesseract_text if tesseract_text else None,
        tesseract_confidence=tesseract_confidence,
    )

    return OcrScanResponse(
        raw_text=result["raw_text"],
        confidence=result["confidence"],
        source=result["source"],
        entities=result.get("entities", {}),
    )


@router.post("/confirm-scan", response_model=OcrConfirmResponse)
async def confirm_scan(
    body: OcrConfirmRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Confirm and optionally create a medicine from OCR results."""
    # TODO: Phase 2 — create medicine from confirmed entities
    return OcrConfirmResponse(confirmed=True)

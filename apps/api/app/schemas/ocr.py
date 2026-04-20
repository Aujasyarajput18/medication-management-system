"""Aujasya — OCR Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OcrEntityResult(BaseModel):
    """Single NLP-extracted entity from OCR text."""
    text: str
    label: str  # DRUG | DOSE | FREQ | DURATION | DOCTOR
    confidence: float = Field(ge=0.0, le=1.0)


class PrescriptionEntities(BaseModel):
    """Structured prescription fields extracted from OCR text."""
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    prescribed_by: str | None = None
    matched_medicine_id: str | None = None
    match_confidence: float | None = Field(None, ge=0.0, le=1.0)


class OcrScanResponse(BaseModel):
    """Response from /ocr/scan-prescription."""
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str  # 'tesseract' | 'llava'
    entities: PrescriptionEntities
    raw_entities: list[OcrEntityResult] = []


class OcrConfirmRequest(BaseModel):
    """Request body for /ocr/confirm-scan."""
    ocr_result_id: str
    confirmed_entities: PrescriptionEntities
    create_medicine: bool = False


class OcrConfirmResponse(BaseModel):
    """Response from /ocr/confirm-scan."""
    medicine_id: str | None = None
    confirmed: bool = True

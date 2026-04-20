"""Aujasya — Pill ID Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PillCandidate(BaseModel):
    """Single pill identification candidate."""
    drug_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    color: str | None = None
    shape: str | None = None
    imprint: str | None = None
    matched_medicine_id: str | None = None


class PillIdResponse(BaseModel):
    """Response from /pill-id/identify."""
    candidates: list[PillCandidate]
    model_version: str
    source: str  # 'client_tfjs' | 'server_onnx'


class BarcodeResult(BaseModel):
    """Response from /pill-id/barcode/{barcode}."""
    medicine_name: str | None = None
    manufacturer: str | None = None
    dosage: str | None = None
    batch_number: str | None = None
    expiry_date: str | None = None
    found: bool = False


class ModelMetadata(BaseModel):
    """Response from /pill-id/model-metadata."""
    model_version: str
    model_url: str
    checksum: str

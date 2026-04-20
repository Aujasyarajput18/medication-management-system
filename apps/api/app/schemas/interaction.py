"""Aujasya — Drug Interaction Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DrugInfo(BaseModel):
    """Drug reference in an interaction pair."""
    rxcui: str
    name: str


class InteractionResult(BaseModel):
    """A single drug-drug interaction result."""
    drug_a: DrugInfo
    drug_b: DrugInfo
    severity: str  # 'contraindicated' | 'major' | 'moderate' | 'minor'
    description: str
    recommendation: str = "Consult your doctor before taking both medications."


class InteractionCheckRequest(BaseModel):
    """Request body for /interactions/check."""
    rxcui_list: list[str] = Field(min_length=2, max_length=10)


class InteractionCheckResponse(BaseModel):
    """Response from /interactions/check."""
    interactions: list[InteractionResult]
    critical_count: int = 0
    major_count: int = 0


class RxcuiLookupResponse(BaseModel):
    """Response from /interactions/medicine/{id}/rxcui."""
    rxcui: str | None = None
    name: str | None = None
    found: bool = False

"""Aujasya — Generic Drug Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class JanAushadhiKendra(BaseModel):
    """Nearest Jan Aushadhi pharmacy."""
    name: str
    address: str
    distance_km: float = Field(ge=0.0)
    lat: float
    lng: float


class GenericAlternative(BaseModel):
    """Single generic drug alternative."""
    name: str
    manufacturer: str
    mrp_per_unit: float
    savings_percent: float = Field(ge=0.0, le=100.0)
    jan_aushadhi: bool = False
    who_gmp: bool = False
    nabl_certified: bool = False
    pmbjp_code: str | None = None
    bioequivalence_min: int = 90
    bioequivalence_max: int = 110
    ranking_score: float = 0.0
    nearest_kendras: list[JanAushadhiKendra] = []


class BrandInfo(BaseModel):
    """Original branded drug info."""
    name: str
    mrp_per_unit: float
    active_ingredient: str


class GenericSearchResponse(BaseModel):
    """Response from /generics/search."""
    brand: BrandInfo
    alternatives: list[GenericAlternative]


class GenericSearchRequest(BaseModel):
    """Query params for /generics/search."""
    brand_name: str
    latitude: float | None = None
    longitude: float | None = None

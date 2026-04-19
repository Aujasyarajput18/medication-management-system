"""
Aujasya — Medicines Router
5 endpoints: list, create, get, update, deactivate.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.medicine import MedicineCreate, MedicineResponse, MedicineUpdate
from app.services.medicine_service import MedicineService

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.get("", response_model=list[MedicineResponse], summary="List medicines")
async def list_medicines(
    user: CurrentUser,
    db: DbSession,
    include_inactive: bool = False,
) -> list[MedicineResponse]:
    """List all medicines for the authenticated patient."""
    service = MedicineService(db)
    return await service.list_medicines(user.id, include_inactive)


@router.post(
    "",
    response_model=MedicineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add medicine",
)
async def create_medicine(
    body: MedicineCreate,
    user: CurrentUser,
    db: DbSession,
) -> MedicineResponse:
    """Create a new medicine with schedules and pre-generate dose logs."""
    if user.role != "patient":
        raise HTTPException(403, "Only patients can add medicines")
    service = MedicineService(db)
    return await service.create_medicine(user.id, body)


@router.get("/{medicine_id}", response_model=MedicineResponse, summary="Get medicine")
async def get_medicine(
    medicine_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> MedicineResponse:
    """Get a single medicine with decrypted details."""
    service = MedicineService(db)
    try:
        return await service.get_medicine(medicine_id, user.id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/{medicine_id}", response_model=MedicineResponse, summary="Update medicine")
async def update_medicine(
    medicine_id: UUID,
    body: MedicineUpdate,
    user: CurrentUser,
    db: DbSession,
) -> MedicineResponse:
    """Update allowed medicine fields."""
    if user.role != "patient":
        raise HTTPException(403, "Only patients can update medicines")
    service = MedicineService(db)
    try:
        return await service.update_medicine(medicine_id, user.id, body)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete(
    "/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate medicine",
)
async def deactivate_medicine(
    medicine_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Soft-delete a medicine (deactivates it and all schedules)."""
    if user.role != "patient":
        raise HTTPException(403, "Only patients can deactivate medicines")
    service = MedicineService(db)
    try:
        await service.deactivate_medicine(medicine_id, user.id)
    except ValueError as e:
        raise HTTPException(404, str(e))

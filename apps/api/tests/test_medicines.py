"""
Aujasya — Medicine Tests
Tests CRUD, schedule generation, [FIX-14] days_of_week, [FIX-16] ON CONFLICT.
"""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient


class TestMedicineCreate:
    """Test POST /api/v1/medicines."""

    @pytest.mark.asyncio
    async def test_create_medicine_success(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/medicines",
            headers=auth_headers,
            json={
                "brand_name": "Metformin 500mg",
                "generic_name": "Metformin Hydrochloride",
                "dosage_value": 500,
                "dosage_unit": "mg",
                "form": "tablet",
                "start_date": date.today().isoformat(),
                "schedules": [
                    {
                        "meal_anchor": "after_breakfast",
                        "dose_quantity": 1,
                        "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                    },
                    {
                        "meal_anchor": "after_dinner",
                        "dose_quantity": 1,
                        "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                    },
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["brand_name"] == "Metformin 500mg"
        assert len(data["schedules"]) == 2

    @pytest.mark.asyncio
    async def test_create_medicine_invalid_dosage_unit(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/medicines",
            headers=auth_headers,
            json={
                "brand_name": "Test",
                "dosage_value": 10,
                "dosage_unit": "invalid_unit",
                "form": "tablet",
                "start_date": date.today().isoformat(),
                "schedules": [{"meal_anchor": "after_breakfast"}],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_medicine_invalid_days_of_week(
        self, client: AsyncClient, auth_headers
    ):
        """[FIX-14] days_of_week values must be 0-6 (0=Sunday)."""
        response = await client.post(
            "/api/v1/medicines",
            headers=auth_headers,
            json={
                "brand_name": "Test",
                "dosage_value": 10,
                "dosage_unit": "mg",
                "form": "tablet",
                "start_date": date.today().isoformat(),
                "schedules": [
                    {
                        "meal_anchor": "after_breakfast",
                        "days_of_week": [0, 1, 7],  # 7 is invalid
                    }
                ],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_medicine_negative_dosage(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post(
            "/api/v1/medicines",
            headers=auth_headers,
            json={
                "brand_name": "Test",
                "dosage_value": -5,
                "dosage_unit": "mg",
                "form": "tablet",
                "start_date": date.today().isoformat(),
                "schedules": [{"meal_anchor": "after_breakfast"}],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_caregiver_cannot_create_medicine(
        self, client: AsyncClient, caregiver_headers
    ):
        response = await client.post(
            "/api/v1/medicines",
            headers=caregiver_headers,
            json={
                "brand_name": "Test",
                "dosage_value": 10,
                "dosage_unit": "mg",
                "form": "tablet",
                "start_date": date.today().isoformat(),
                "schedules": [{"meal_anchor": "after_breakfast"}],
            },
        )
        assert response.status_code == 403


class TestMedicineList:
    """Test GET /api/v1/medicines."""

    @pytest.mark.asyncio
    async def test_list_medicines_empty(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/medicines", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

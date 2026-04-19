"""
Aujasya — Dose Tests
Tests dose logging, offline sync, [FIX-15] calendar, streak calculation.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestDosesToday:
    """Test GET /api/v1/doses/today."""

    @pytest.mark.asyncio
    async def test_today_doses_empty(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/doses/today", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_today_doses_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/doses/today")
        assert response.status_code == 401


class TestCalendar:
    """Test GET /api/v1/doses/calendar."""

    @pytest.mark.asyncio
    async def test_calendar_valid_month(self, client: AsyncClient, auth_headers):
        """[FIX-15] Calendar accepts month=YYYY-MM only."""
        response = await client.get(
            "/api/v1/doses/calendar",
            headers=auth_headers,
            params={"month": "2025-01"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert data["month"] == "2025-01"

    @pytest.mark.asyncio
    async def test_calendar_invalid_month_format(
        self, client: AsyncClient, auth_headers
    ):
        """[FIX-15] Reject invalid month formats."""
        response = await client.get(
            "/api/v1/doses/calendar",
            headers=auth_headers,
            params={"month": "January 2025"},
        )
        assert response.status_code == 422


class TestStreak:
    """Test GET /api/v1/doses/streak."""

    @pytest.mark.asyncio
    async def test_streak_initial(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/doses/streak", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "adherence_30d" in data

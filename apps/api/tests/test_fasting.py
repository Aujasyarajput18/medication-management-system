"""
Aujasya — Fasting Service Unit Tests
Tests NEVER_AUTO_RESCHEDULE guard and schedule adjustment logic.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fasting_service import FastingService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def fasting_service(mock_db):
    return FastingService(mock_db)


class TestNeverAutoReschedule:
    """Verify clinical safety guard for dangerous medication classes."""

    def test_insulin_blocked(self, fasting_service):
        result = fasting_service.check_reschedule_safety("insulin glargine")
        assert result["blocked"] is True
        assert result["severity"] == "critical"

    def test_warfarin_blocked(self, fasting_service):
        result = fasting_service.check_reschedule_safety("warfarin")
        assert result["blocked"] is True

    def test_digoxin_blocked(self, fasting_service):
        result = fasting_service.check_reschedule_safety("digoxin")
        assert result["blocked"] is True

    def test_safe_medicine_allowed(self, fasting_service):
        result = fasting_service.check_reschedule_safety("paracetamol")
        assert result["blocked"] is False

    def test_case_insensitive_check(self, fasting_service):
        result = fasting_service.check_reschedule_safety("INSULIN")
        assert result["blocked"] is True

    def test_partial_match_blocked(self, fasting_service):
        """'insulin lispro' should match 'insulin lispro' in the set."""
        result = fasting_service.check_reschedule_safety("insulin lispro")
        assert result["blocked"] is True


class TestMealAnchorMapping:
    """Test that fasting schedules correctly remap meal anchors."""

    def test_breakfast_remaps_to_suhoor(self, fasting_service):
        mapping = fasting_service.get_fasting_meal_mapping("ramadan")
        assert mapping.get("breakfast") == "suhoor"

    def test_dinner_remaps_to_iftar(self, fasting_service):
        mapping = fasting_service.get_fasting_meal_mapping("ramadan")
        assert mapping.get("dinner") == "iftar"

    def test_bedtime_unchanged(self, fasting_service):
        mapping = fasting_service.get_fasting_meal_mapping("ramadan")
        assert mapping.get("bedtime") == "bedtime"

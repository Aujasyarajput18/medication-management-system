"""
Aujasya — Journal Service Unit Tests
Tests NLP symptom normalization and 7-day pattern detection.
"""
import pytest
import pytest_asyncio
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.journal_service import JournalService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def journal_service(mock_db):
    return JournalService(mock_db)


class TestSymptomNormalization:
    """Test the curated vocabulary-based symptom normalizer."""

    def test_normalize_english_symptom(self, journal_service):
        normalized = journal_service.normalize_symptoms("I feel nausea and dizziness")
        assert "nausea" in normalized
        assert "dizziness" in normalized

    def test_normalize_hindi_symptom(self, journal_service):
        normalized = journal_service.normalize_symptoms("chakkar aa raha hai")
        assert "dizziness" in normalized

    def test_normalize_multiple_synonyms(self, journal_service):
        normalized = journal_service.normalize_symptoms("vomiting and ulti")
        # Both should map to "nausea"
        assert "nausea" in normalized

    def test_normalize_unknown_symptom(self, journal_service):
        normalized = journal_service.normalize_symptoms("xyz unknown symptom abc")
        # Should return empty or no matches for unknown terms
        assert isinstance(normalized, list)

    def test_normalize_mixed_language(self, journal_service):
        normalized = journal_service.normalize_symptoms(
            "headache and sir dard with rash"
        )
        assert "headache" in normalized


class TestPatternDetection:
    """Test the 7-day rolling window pattern flagger."""

    def test_flag_threshold_met(self, journal_service):
        """≥3 same symptom in 7 days → flagged."""
        entries = []
        today = date.today()
        for i in range(3):
            entries.append({
                "symptom_normalized": ["nausea"],
                "onset_date": today - timedelta(days=i),
                "severity": "moderate",
            })

        patterns = journal_service.detect_patterns(entries, period_days=7)
        flagged = [p for p in patterns if p["count"] >= 3]
        assert len(flagged) >= 1
        assert flagged[0]["symptom"] == "nausea"

    def test_no_flag_below_threshold(self, journal_service):
        """<3 occurrences → not flagged."""
        entries = [
            {
                "symptom_normalized": ["nausea"],
                "onset_date": date.today(),
                "severity": "mild",
            },
            {
                "symptom_normalized": ["nausea"],
                "onset_date": date.today() - timedelta(days=1),
                "severity": "mild",
            },
        ]

        patterns = journal_service.detect_patterns(entries, period_days=7)
        flagged = [p for p in patterns if p["count"] >= 3]
        assert len(flagged) == 0

    def test_separate_symptoms_tracked_independently(self, journal_service):
        """Different symptoms are counted separately."""
        today = date.today()
        entries = [
            {"symptom_normalized": ["nausea"], "onset_date": today, "severity": "mild"},
            {"symptom_normalized": ["headache"], "onset_date": today, "severity": "mild"},
            {"symptom_normalized": ["nausea"], "onset_date": today - timedelta(days=1), "severity": "mild"},
        ]

        patterns = journal_service.detect_patterns(entries, period_days=7)
        nausea_pattern = [p for p in patterns if p["symptom"] == "nausea"]
        assert len(nausea_pattern) == 1
        assert nausea_pattern[0]["count"] == 2

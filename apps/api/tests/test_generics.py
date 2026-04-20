"""
Aujasya — Generic Service Unit Tests
Tests trust-score ranking algorithm and Haversine distance.
"""
import pytest
from unittest.mock import AsyncMock

from app.services.generic_service import GenericService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def generic_service(mock_db, mock_redis):
    return GenericService(mock_db, mock_redis)


class TestTrustScoreRanking:
    """Verify trust-score ranking algorithm."""

    def test_who_gmp_scores_higher(self, generic_service):
        alt_a = {"who_gmp": True, "nabl_certified": False, "jan_aushadhi": False, "mrp_per_unit": 5.0}
        alt_b = {"who_gmp": False, "nabl_certified": False, "jan_aushadhi": False, "mrp_per_unit": 5.0}
        score_a = generic_service.compute_trust_score(alt_a)
        score_b = generic_service.compute_trust_score(alt_b)
        assert score_a > score_b

    def test_nabl_adds_to_score(self, generic_service):
        alt = {"who_gmp": False, "nabl_certified": True, "jan_aushadhi": False, "mrp_per_unit": 5.0}
        score = generic_service.compute_trust_score(alt)
        assert score > 0

    def test_jan_aushadhi_adds_to_score(self, generic_service):
        alt = {"who_gmp": False, "nabl_certified": False, "jan_aushadhi": True, "mrp_per_unit": 2.0}
        score = generic_service.compute_trust_score(alt)
        assert score > 0

    def test_ranking_order(self, generic_service):
        alternatives = [
            {"name": "A", "who_gmp": True, "nabl_certified": True, "jan_aushadhi": True, "mrp_per_unit": 2.0},
            {"name": "B", "who_gmp": False, "nabl_certified": False, "jan_aushadhi": False, "mrp_per_unit": 8.0},
            {"name": "C", "who_gmp": True, "nabl_certified": False, "jan_aushadhi": False, "mrp_per_unit": 5.0},
        ]
        ranked = generic_service.rank_alternatives(alternatives)
        assert ranked[0]["name"] == "A"  # Highest trust score


class TestHaversineDistance:
    """Test Haversine distance calculation."""

    def test_same_point_zero_distance(self, generic_service):
        dist = generic_service.haversine_km(28.6139, 77.2090, 28.6139, 77.2090)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self, generic_service):
        # Delhi to Gurgaon ≈ 30km
        dist = generic_service.haversine_km(28.6139, 77.2090, 28.4595, 77.0266)
        assert 20 < dist < 40

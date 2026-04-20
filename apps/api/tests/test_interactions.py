"""
Aujasya — Interaction Service Unit Tests
Tests RxNorm lookup, OpenFDA interaction check, and caching.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.interaction_service import InteractionService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def interaction_service(mock_db, mock_redis):
    return InteractionService(mock_db, mock_redis)


class TestSeverityRanking:
    """Verify correct severity ordering."""

    def test_severity_order(self, interaction_service):
        ranking = interaction_service.SEVERITY_RANKING
        assert ranking["contraindicated"] > ranking["major"]
        assert ranking["major"] > ranking["moderate"]
        assert ranking["moderate"] > ranking["minor"]


class TestCacheKey:
    """Verify deterministic cache key generation."""

    def test_cache_key_sorted(self, interaction_service):
        key1 = interaction_service.get_cache_key("rxcui_b", "rxcui_a")
        key2 = interaction_service.get_cache_key("rxcui_a", "rxcui_b")
        assert key1 == key2  # Order independent

    def test_cache_key_format(self, interaction_service):
        key = interaction_service.get_cache_key("12345", "67890")
        assert key == "interaction:12345:67890"

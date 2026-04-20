"""
Aujasya — OCR Service Unit Tests
Tests the Tesseract → LLaVA state machine and confidence thresholds.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ocr_service import OcrService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def ocr_service(mock_db, mock_redis):
    return OcrService(mock_db, mock_redis)


class TestConfidenceThreshold:
    """Verify the Tesseract → LLaVA fallback logic."""

    def test_high_confidence_returns_tesseract(self, ocr_service):
        """Confidence ≥ 0.65 → use Tesseract result directly."""
        result = ocr_service.evaluate_confidence(0.75, "tesseract")
        assert result["use_llava"] is False
        assert result["source"] == "tesseract"

    def test_low_confidence_triggers_llava(self, ocr_service):
        """Confidence < 0.65 → try LLaVA."""
        result = ocr_service.evaluate_confidence(0.40, "tesseract")
        assert result["use_llava"] is True

    def test_boundary_confidence(self, ocr_service):
        """Exactly 0.65 → use Tesseract (boundary inclusive)."""
        result = ocr_service.evaluate_confidence(0.65, "tesseract")
        assert result["use_llava"] is False


class TestOcrResultValidation:
    """Verify OCR result structure validation."""

    def test_valid_result_has_required_fields(self, ocr_service):
        result = {
            "raw_text": "Paracetamol 500mg",
            "confidence": 0.85,
            "source": "tesseract",
        }
        assert ocr_service.validate_result(result) is True

    def test_empty_text_invalid(self, ocr_service):
        result = {
            "raw_text": "",
            "confidence": 0.85,
            "source": "tesseract",
        }
        assert ocr_service.validate_result(result) is False

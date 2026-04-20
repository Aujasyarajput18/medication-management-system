"""
Aujasya — OCR Service
State machine: Tesseract first → LLaVA fallback → low-confidence partial result.
All decisions logged to ai_decision_logs table.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_decision_log import AiDecisionLog
from app.services.llava_service import LlavaService
from app.services.prescription_parser_service import PrescriptionParserService

logger = structlog.get_logger()

TESSERACT_CONFIDENCE_THRESHOLD = 0.65


class OcrService:
    """
    OCR state machine for prescription scanning.

    Flow:
    1. Tesseract processes image (client sends pre-OCR'd text, or server does it)
    2. If confidence >= 0.65 → return Tesseract result
    3. If confidence < 0.65 → try LLaVA
    4. If LLaVA unavailable → return partial Tesseract with low-confidence flag
    5. All paths write to ai_decision_logs
    """

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.parser = PrescriptionParserService(db)
        self.llava = LlavaService(redis)

    async def process_prescription(
        self,
        patient_id: uuid.UUID,
        image_bytes: bytes | None = None,
        tesseract_text: str | None = None,
        tesseract_confidence: float = 0.0,
    ) -> dict:
        """
        Process a prescription through the OCR pipeline.
        Returns structured result with source and confidence.
        """
        # ── Path 1: Tesseract confidence is good enough ──────────────
        if tesseract_text and tesseract_confidence >= TESSERACT_CONFIDENCE_THRESHOLD:
            entities = self.parser.extract_entities(tesseract_text)

            if entities.get("drug_name") or entities.get("dosage"):
                medicine_id, match_conf = await self.parser.fuzzy_match_medicine(
                    tesseract_text, patient_id,
                )
                entities["matched_medicine_id"] = medicine_id
                entities["match_confidence"] = match_conf

            result = {
                "raw_text": tesseract_text,
                "confidence": tesseract_confidence,
                "source": "tesseract",
                "entities": entities,
            }

            await self._log_decision(patient_id, result, "pending")
            return result

        # ── Path 2: Try LLaVA for better results ─────────────────────
        if image_bytes and await self.llava.is_available():
            llava_result = await self.llava.ocr_image(image_bytes)

            if llava_result and llava_result.get("confidence", 0) > 0:
                result = {
                    "raw_text": llava_result.get("raw_text", ""),
                    "confidence": llava_result.get("confidence", 0.5),
                    "source": "llava",
                    "entities": llava_result.get("entities", {}),
                }
                await self._log_decision(patient_id, result, "pending")
                return result

        # ── Path 3: Fallback — partial Tesseract with warning ────────
        entities = {}
        if tesseract_text:
            entities = self.parser.extract_entities(tesseract_text)

        result = {
            "raw_text": tesseract_text or "",
            "confidence": min(tesseract_confidence, 0.4),
            "source": "tesseract",
            "confidence_flag": "low",
            "user_warning": "Low confidence — please review all fields carefully",
            "entities": entities,
        }

        await self._log_decision(patient_id, result, "pending")
        return result

    async def _log_decision(
        self, patient_id: uuid.UUID, result: dict, user_action: str,
    ) -> None:
        """Write to ai_decision_logs for medico-legal trail."""
        log = AiDecisionLog(
            patient_id=patient_id,
            decision_type="ocr_scan",
            model_version=f"tesseract+llava" if result.get("source") == "llava" else "tesseract",
            confidence=Decimal(str(result.get("confidence", 0))),
            input_summary=f"Prescription scan, source={result.get('source')}",
            output_summary=result,
            user_action=user_action,
        )
        self.db.add(log)
        await self.db.flush()

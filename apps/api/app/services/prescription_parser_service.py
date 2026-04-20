"""
Aujasya — Prescription Parser Service
NER extraction + fuzzy matching against the medicines table.
Uses spaCy for entity recognition and rapidfuzz for medicine name matching.
"""

from __future__ import annotations

import re
import uuid

import structlog
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medicine import Medicine

logger = structlog.get_logger()

# Indian prescription frequency patterns
FREQUENCY_PATTERNS = {
    r'\b1\s*[-–]\s*0\s*[-–]\s*1\b': 'morning-night',
    r'\b1\s*[-–]\s*1\s*[-–]\s*1\b': 'morning-afternoon-night',
    r'\b0\s*[-–]\s*0\s*[-–]\s*1\b': 'night-only',
    r'\b1\s*[-–]\s*0\s*[-–]\s*0\b': 'morning-only',
    r'\bOD\b': 'once-daily',
    r'\bBD\b': 'twice-daily',
    r'\bTDS\b': 'thrice-daily',
    r'\bQID\b': 'four-times-daily',
    r'\bSOS\b': 'as-needed',
    r'\bHS\b': 'at-bedtime',
    r'\bAC\b': 'before-food',
    r'\bPC\b': 'after-food',
}

DOSAGE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(mg|mcg|ml|g|IU|units?)', re.IGNORECASE)
DURATION_PATTERN = re.compile(r'(\d+)\s*(days?|weeks?|months?)', re.IGNORECASE)
DOCTOR_PATTERN = re.compile(r'(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE)


class PrescriptionParserService:
    """Extracts structured entities from OCR text."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def extract_entities(self, raw_text: str) -> dict:
        """Extract prescription entities using regex patterns."""
        entities = {
            "drug_name": None, "dosage": None, "frequency": None,
            "duration": None, "prescribed_by": None, "instructions": None,
        }

        # Extract dosage
        dosage_match = DOSAGE_PATTERN.search(raw_text)
        if dosage_match:
            entities["dosage"] = dosage_match.group(0)

        # Extract frequency
        for pattern, label in FREQUENCY_PATTERNS.items():
            if re.search(pattern, raw_text, re.IGNORECASE):
                entities["frequency"] = label
                break

        # Extract duration
        dur_match = DURATION_PATTERN.search(raw_text)
        if dur_match:
            entities["duration"] = dur_match.group(0)

        # Extract doctor name
        doc_match = DOCTOR_PATTERN.search(raw_text)
        if doc_match:
            entities["prescribed_by"] = doc_match.group(1)

        # Extract meal instructions
        if re.search(r'\b(?:after|with)\s+(?:food|meal|breakfast|lunch|dinner)\b', raw_text, re.IGNORECASE):
            entities["instructions"] = "after food"
        elif re.search(r'\b(?:before|empty)\s+(?:food|meal|stomach)\b', raw_text, re.IGNORECASE):
            entities["instructions"] = "before food"

        return entities

    async def fuzzy_match_medicine(
        self, drug_text: str, patient_id: uuid.UUID
    ) -> tuple[str | None, float]:
        """
        Fuzzy-match extracted drug name against patient's existing medicines.
        Returns (medicine_id, confidence) or (None, 0.0).
        """
        stmt = select(Medicine).where(
            Medicine.patient_id == patient_id,
            Medicine.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        medicines = result.scalars().all()

        if not medicines:
            return None, 0.0

        choices = {str(m.id): m.brand_name for m in medicines}
        match = process.extractOne(
            drug_text,
            choices,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=60,
        )

        if match:
            matched_name, score, medicine_id = match
            return medicine_id, score / 100.0

        return None, 0.0

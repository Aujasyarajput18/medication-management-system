"""
Aujasya — Side-Effect Journal Service
Rule-based NLP with curated ~200-term symptom vocabulary.
Pattern detection: 3+ occurrences of same symptom in 7 days → flagged.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import structlog
from rapidfuzz import fuzz, process
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dose_log import DoseLog
from app.models.side_effect_entry import SideEffectEntry

logger = structlog.get_logger()

# ── Curated symptom vocabulary (~200 terms) ──────────────────────────────
# English + Hindi + transliteration for common medication side effects
SYMPTOM_VOCABULARY: dict[str, list[str]] = {
    "nausea": ["nausea", "ji machlana", "ulti jaisa", "matlai", "matli"],
    "vomiting": ["vomiting", "ulti", "vomit", "qay"],
    "headache": ["headache", "sir dard", "sar dard", "sir mein dard", "cephalalgia"],
    "dizziness": ["dizziness", "chakkar", "chakkar aana", "vertigo", "sir ghoomna"],
    "drowsiness": ["drowsiness", "neend aana", "sust", "drowsy", "uungh"],
    "insomnia": ["insomnia", "neend nahi aana", "sleeplessness", "neend na aana"],
    "diarrhea": ["diarrhea", "dast", "loose motion", "pet kharab", "pait kharab"],
    "constipation": ["constipation", "kabz", "qabz", "pet saaf nahi"],
    "stomach_pain": ["stomach pain", "pet dard", "pet mein dard", "abdominal pain"],
    "acidity": ["acidity", "gas", "acidity", "pet mein jalan", "seene mein jalan"],
    "rash": ["rash", "dane", "khujli", "skin rash", "daane", "allergy"],
    "itching": ["itching", "khujli", "kharish", "pruritus"],
    "fatigue": ["fatigue", "thakaan", "kamzori", "weakness", "thakan"],
    "muscle_pain": ["muscle pain", "body pain", "badan dard", "muscle ache", "myalgia"],
    "joint_pain": ["joint pain", "jod dard", "joint ache", "arthralgia"],
    "cough": ["cough", "khansi", "khaansi", "dry cough", "sukhi khansi"],
    "fever": ["fever", "bukhar", "bukhaar", "temperature"],
    "swelling": ["swelling", "sujan", "soojan", "edema"],
    "blurred_vision": ["blurred vision", "dhundhla dikhna", "nazar kamzor"],
    "dry_mouth": ["dry mouth", "mooh sukha", "munh sukhna"],
    "appetite_loss": ["appetite loss", "bhookh na lagna", "khana nahi khane ka mann"],
    "weight_gain": ["weight gain", "wazan badhna", "motapa"],
    "weight_loss": ["weight loss", "wazan ghatna", "wazan kam hona"],
    "palpitations": ["palpitations", "dil ki dhadkan tez", "heartbeat fast"],
    "breathing_difficulty": ["breathing difficulty", "saans lene mein taklif", "dyspnea"],
    "anxiety": ["anxiety", "ghabrahat", "tension", "chinta"],
    "depression": ["depression", "udaasi", "depression", "sad feeling"],
    "hair_loss": ["hair loss", "baal girna", "bal jharna", "alopecia"],
    "bruising": ["bruising", "neel padna", "chot ka nishan"],
    "bleeding": ["bleeding", "khoon aana", "bleeding", "hemorrhage"],
    "hypoglycemia": ["hypoglycemia", "sugar gir gaya", "low sugar", "shakkar kam"],
    "urinary_frequency": ["urinary frequency", "baar baar peshab", "frequent urination"],
}

# Flatten for fast lookup
ALL_SYMPTOMS: dict[str, str] = {}
for canonical, variants in SYMPTOM_VOCABULARY.items():
    for v in variants:
        ALL_SYMPTOMS[v.lower()] = canonical


class JournalService:
    """Side-effect journal with NLP normalization and pattern detection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_entry(
        self,
        patient_id: uuid.UUID,
        symptom_text: str,
        severity: str,
        onset_date: date,
        input_method: str,
        medicine_id: uuid.UUID | None = None,
        dose_log_id: uuid.UUID | None = None,
        voice_transcript: str | None = None,
    ) -> SideEffectEntry:
        """Create a journal entry with NLP symptom normalization."""
        normalized = self._normalize_symptoms(symptom_text)

        entry = SideEffectEntry(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            medicine_id=medicine_id,
            symptom_text=symptom_text,
            symptom_normalized=normalized,
            severity=severity,
            onset_date=onset_date,
            input_method=input_method,
            voice_transcript=voice_transcript,
        )
        self.db.add(entry)

        # Link to dose log if provided
        if dose_log_id:
            stmt = select(DoseLog).where(DoseLog.id == dose_log_id)
            result = await self.db.execute(stmt)
            dose_log = result.scalar_one_or_none()
            if dose_log:
                dose_log.has_journal_entry = True

        await self.db.flush()

        # Check for patterns (3+ in 7 days)
        await self._check_patterns(patient_id, entry, normalized)

        return entry

    def _normalize_symptoms(self, text: str) -> list[str]:
        """
        Normalize symptom text to canonical terms using fuzzy matching.
        Handles Hindi, English, and transliteration.
        """
        words = text.lower().strip()
        matched: set[str] = set()

        # Direct lookup first
        for term, canonical in ALL_SYMPTOMS.items():
            if term in words:
                matched.add(canonical)

        # Fuzzy match if no direct hits
        if not matched:
            all_terms = list(ALL_SYMPTOMS.keys())
            results = process.extract(words, all_terms, scorer=fuzz.token_set_ratio, limit=3, score_cutoff=70)
            for term, score, _ in results:
                matched.add(ALL_SYMPTOMS[term])

        return list(matched) if matched else [words]

    async def _check_patterns(
        self, patient_id: uuid.UUID, entry: SideEffectEntry, normalized: list[str],
    ) -> None:
        """Flag entry if 3+ occurrences of same symptom in 7 days."""
        seven_days_ago = entry.onset_date - timedelta(days=7)

        for symptom in normalized:
            stmt = select(func.count()).where(
                and_(
                    SideEffectEntry.patient_id == patient_id,
                    SideEffectEntry.symptom_normalized.any(symptom),
                    SideEffectEntry.onset_date >= seven_days_ago,
                )
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0

            if count >= 3:
                entry.is_flagged = True
                entry.flag_reason = (
                    f"Pattern detected: '{symptom}' reported {count} times in 7 days. "
                    f"Consider consulting your doctor."
                )
                logger.warning(
                    "symptom_pattern_flagged",
                    patient_id=str(patient_id),
                    symptom=symptom,
                    count=count,
                )
                break

    async def get_patterns(self, patient_id: uuid.UUID, period_days: int = 30) -> list[dict]:
        """Detect recurring symptom patterns over a period."""
        since = date.today() - timedelta(days=period_days)

        stmt = select(SideEffectEntry).where(
            and_(
                SideEffectEntry.patient_id == patient_id,
                SideEffectEntry.onset_date >= since,
            )
        ).order_by(SideEffectEntry.onset_date.desc())

        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        # Count symptom occurrences
        symptom_counts: dict[str, dict] = {}
        for entry in entries:
            for sym in (entry.symptom_normalized or []):
                if sym not in symptom_counts:
                    symptom_counts[sym] = {
                        "symptom": sym,
                        "count": 0,
                        "first_occurrence": entry.onset_date,
                        "last_occurrence": entry.onset_date,
                    }
                symptom_counts[sym]["count"] += 1
                if entry.onset_date < symptom_counts[sym]["first_occurrence"]:
                    symptom_counts[sym]["first_occurrence"] = entry.onset_date
                if entry.onset_date > symptom_counts[sym]["last_occurrence"]:
                    symptom_counts[sym]["last_occurrence"] = entry.onset_date

        patterns = [v for v in symptom_counts.values() if v["count"] >= 2]
        patterns.sort(key=lambda x: x["count"], reverse=True)
        return patterns

"""
Aujasya — Voice Intent Classification Service
Classifies STT transcripts into dose-logging intents with slot extraction.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger()

# Intent patterns — Hindi + English + transliteration
INTENT_PATTERNS = [
    {
        "type": "log_dose_taken",
        "patterns": [
            r"(?:dawa|dawai|medicine|tablet|goli)\s+(?:le\s*li|kha\s*li|taken|ley?\s*liya)",
            r"(?:taken|took)\s+(?:my\s+)?(?:medicine|dose|tablet|pill)",
            r"(?:le\s*liya|kha\s*liya)\s+(?:hai|h)",
        ],
    },
    {
        "type": "log_dose_skipped",
        "patterns": [
            r"(?:dawa|medicine|tablet|goli)\s+(?:nahi|nhi|skip|chhod)",
            r"(?:skip|missed|didn't take)\s+(?:my\s+)?(?:medicine|dose)",
            r"(?:nahi|nhi)\s+(?:li|khai|liya)",
        ],
    },
    {
        "type": "query_next_dose",
        "patterns": [
            r"(?:agla|next|agle)\s+(?:dose|dawa|medicine|dawai)",
            r"(?:kab|when)\s+(?:leni|lena|take)\s+(?:hai|h|is)",
            r"when\s+(?:is\s+)?(?:my\s+)?next\s+(?:dose|medicine)",
        ],
    },
    {
        "type": "query_streak",
        "patterns": [
            r"(?:streak|series|lagatar|kitne din)",
            r"(?:how\s+many|kitne)\s+(?:days?|din)",
        ],
    },
]


class IntentService:
    """Classifies voice transcripts into medication management intents."""

    def classify(self, transcript: str, language: str = "hi") -> dict:
        """
        Classify a transcript into an intent with slot extraction.
        Returns: {"type": str, "slots": dict, "confidence": float}
        """
        text = transcript.strip().lower()

        if not text:
            return {"type": "unknown", "slots": {}, "confidence": 0.0}

        for intent_def in INTENT_PATTERNS:
            for pattern in intent_def["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    slots = self._extract_slots(text, intent_def["type"])
                    return {
                        "type": intent_def["type"],
                        "slots": slots,
                        "confidence": 0.85,
                    }

        return {"type": "unknown", "slots": {}, "confidence": 0.1}

    def _extract_slots(self, text: str, intent_type: str) -> dict:
        """Extract relevant slots from transcript based on intent type."""
        slots: dict[str, str] = {}

        # Try to extract medicine name
        med_patterns = [
            r"(?:Tab|Tablet|Cap|Capsule|Syp|Syrup)\s+(\w+(?:\s+\d+\s*mg)?)",
            r"(\w+)\s+(?:ki dawa|medicine|tablet)",
        ]
        for pattern in med_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                slots["medicine_name"] = match.group(1).strip()
                break

        # Time extraction
        time_patterns = [
            (r"(?:subah|morning|savere)", "morning"),
            (r"(?:dopahar|afternoon|lunch)", "afternoon"),
            (r"(?:sham|evening|shaam)", "evening"),
            (r"(?:raat|night|sone se pehle)", "night"),
        ]
        for pattern, slot_val in time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                slots["time_of_day"] = slot_val
                break

        return slots

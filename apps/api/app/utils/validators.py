"""
Aujasya — Input Validators
Indian phone number and other field validators.
"""

from __future__ import annotations

import re


def validate_indian_phone(phone: str) -> bool:
    """
    Validate an Indian mobile phone number in E.164 format.
    
    Format: +91[6-9]XXXXXXXXX (total 13 chars including +91)
    Indian mobile numbers start with 6, 7, 8, or 9 after the country code.
    """
    return bool(re.match(r"^\+91[6-9]\d{9}$", phone))


def validate_abha_id(abha_id: str) -> bool:
    """
    Validate ABHA ID format (14-digit number).
    Phase 3 feature — basic format validation only.
    """
    return bool(re.match(r"^\d{14}$", abha_id))


def validate_language_code(code: str) -> bool:
    """Validate supported language code."""
    return code in {"en", "hi", "ta", "te", "bn", "mr"}


def sanitize_phone_for_logging(phone: str) -> str:
    """
    Mask phone number for logging — show only last 4 digits.
    NEVER log full phone numbers in production.
    """
    if len(phone) >= 4:
        return f"***{phone[-4:]}"
    return "****"

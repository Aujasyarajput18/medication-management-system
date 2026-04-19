"""
Aujasya — Cryptographically Secure OTP Generation
DO NOT use random.randint() or math.floor(random.random()) — not secure.
"""

from __future__ import annotations

import secrets

from passlib.context import CryptContext

# bcrypt context for OTP hashing (12 rounds)
otp_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP.
    
    Uses secrets.randbelow() which uses the OS CSPRNG.
    Range: 100000–999999 (guaranteed 6 digits, uniform distribution).
    """
    return str(secrets.randbelow(900000) + 100000)


def hash_otp(otp: str) -> str:
    """Hash an OTP with bcrypt (12 rounds) for storage."""
    return otp_hasher.hash(otp)


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify an OTP against its bcrypt hash (constant-time comparison)."""
    return otp_hasher.verify(plain_otp, hashed_otp)


def generate_refresh_token() -> str:
    """Generate a 256-bit random token for refresh tokens."""
    return secrets.token_hex(32)

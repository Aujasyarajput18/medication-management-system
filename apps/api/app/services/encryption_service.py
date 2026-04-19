"""
Aujasya — AES-256-GCM Field Encryption Service
Encrypts sensitive health data fields at rest.

Key features:
- AES-256-GCM (authenticated encryption: confidentiality + integrity)
- Key derivation from master key via HKDF-SHA256 with per-field salt
- Key versioning for rotation support
- Format: "v1:{base64(nonce)}:{base64(ciphertext)}:{base64(tag)}"

NEVER log decrypted values. NEVER store the master key in the database.
"""

from __future__ import annotations

import base64
import os
import structlog

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from app.config import settings

logger = structlog.get_logger()


class EncryptionService:
    """AES-256-GCM field-level encryption with key versioning."""

    def __init__(self) -> None:
        self._master_key = bytes.fromhex(settings.ENCRYPTION_MASTER_KEY)
        self._key_version = settings.ENCRYPTION_KEY_VERSION
        self._key_cache: dict[str, bytes] = {}

    def _derive_key(self, field_name: str) -> bytes:
        """
        Derive a field-specific AES-256 key from the master key using HKDF-SHA256.
        Each field gets its own derived key (different salt = different key).
        """
        if field_name in self._key_cache:
            return self._key_cache[field_name]

        salt = f"aujasya_{field_name}_{self._key_version}".encode("utf-8")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            info=b"aujasya-field-encryption",
        )
        derived_key = hkdf.derive(self._master_key)
        self._key_cache[field_name] = derived_key
        return derived_key

    def encrypt_field(self, plaintext: str, field_name: str) -> str:
        """
        Encrypt a plaintext string using AES-256-GCM.
        
        Args:
            plaintext: The string to encrypt
            field_name: Name of the field (used for key derivation)
        
        Returns:
            Encrypted string in format "v1:{nonce}:{ciphertext}:{tag}"
        """
        if not plaintext:
            return ""

        key = self._derive_key(field_name)
        aesgcm = AESGCM(key)

        # 96-bit nonce (12 bytes) — standard for GCM
        nonce = os.urandom(12)

        # AES-GCM produces ciphertext + tag in a single output
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Split: last 16 bytes are the tag, rest is ciphertext
        ciphertext = ciphertext_and_tag[:-16]
        tag = ciphertext_and_tag[-16:]

        nonce_b64 = base64.b64encode(nonce).decode("ascii")
        ct_b64 = base64.b64encode(ciphertext).decode("ascii")
        tag_b64 = base64.b64encode(tag).decode("ascii")

        return f"{self._key_version}:{nonce_b64}:{ct_b64}:{tag_b64}"

    def decrypt_field(self, encrypted: str, field_name: str) -> str:
        """
        Decrypt an AES-256-GCM encrypted field.
        
        Args:
            encrypted: Encrypted string in format "version:nonce:ciphertext:tag"
            field_name: Name of the field (used for key derivation)
        
        Returns:
            Decrypted plaintext string
        
        Raises:
            ValueError: If the encrypted format is invalid
            cryptography.exceptions.InvalidTag: If decryption fails (tampered data)
        """
        if not encrypted:
            return ""

        parts = encrypted.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid encrypted field format")

        version, nonce_b64, ct_b64, tag_b64 = parts

        # For key rotation: derive key using the version from the stored data
        original_version = self._key_version
        self._key_version = version
        key = self._derive_key(field_name)
        self._key_version = original_version

        aesgcm = AESGCM(key)

        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ct_b64)
        tag = base64.b64decode(tag_b64)

        # Recombine ciphertext + tag for decryption
        ciphertext_and_tag = ciphertext + tag
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)

        return plaintext_bytes.decode("utf-8")

    def encrypt_bytes(self, plaintext: str, field_name: str) -> bytes:
        """Encrypt and return as bytes for BYTEA storage."""
        encrypted_str = self.encrypt_field(plaintext, field_name)
        return encrypted_str.encode("utf-8")

    def decrypt_bytes(self, encrypted_bytes: bytes | None, field_name: str) -> str | None:
        """Decrypt from BYTEA bytes."""
        if encrypted_bytes is None:
            return None
        encrypted_str = encrypted_bytes.decode("utf-8")
        return self.decrypt_field(encrypted_str, field_name)


# Singleton instance
encryption_service = EncryptionService()

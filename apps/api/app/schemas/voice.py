"""Aujasya — Voice Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceIntent(BaseModel):
    """Classified voice intent with extracted slots."""
    type: str  # 'log_dose_taken' | 'log_dose_skipped' | 'query_next_dose' | 'query_streak' | 'add_medicine' | 'unknown'
    slots: dict[str, str] = {}
    confidence: float = Field(ge=0.0, le=1.0)


class SttResponse(BaseModel):
    """Response from /voice/stt."""
    transcript: str
    intent: VoiceIntent
    language: str


class TtsRequest(BaseModel):
    """Request body for /voice/tts."""
    text: str = Field(min_length=1, max_length=500)
    language: str = "hi"
    voice_gender: str = "female"


class LogIntentRequest(BaseModel):
    """Request body for /voice/log-intent."""
    intent: VoiceIntent
    confirmed: bool = False


class LogIntentResponse(BaseModel):
    """Response from /voice/log-intent."""
    action_taken: str
    result: dict | None = None
    message: str

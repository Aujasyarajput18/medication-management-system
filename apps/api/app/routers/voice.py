"""
Aujasya — Voice Router
STT/TTS endpoints and intent-based dose logging.
Requires 'voice_processing' consent.
Audio is NEVER persisted (DPDPA compliance).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas.voice import SttResponse, TtsRequest, VoiceIntent
from app.services.bhashini_service import BhashiniService
from app.services.intent_service import IntentService

logger = structlog.get_logger()

router = APIRouter(prefix="/voice", tags=["Voice Interface"])


async def get_redis() -> Redis:
    from app.config import settings
    return Redis.from_url(settings.REDIS_URL)


@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("hi"),
    redis: Redis = Depends(get_redis),
):
    """
    Convert speech to text and classify intent.
    Audio is processed in memory — NEVER stored to disk or database.
    """
    audio_bytes = await audio.read()

    # Hard limit: 30 seconds of audio (~480KB at 16kHz mono WAV)
    if len(audio_bytes) > 1024 * 1024:
        raise HTTPException(413, "Audio exceeds 1MB limit (~30s)")

    bhashini = BhashiniService(redis)
    stt_result = await bhashini.speech_to_text(audio_bytes, language)

    if stt_result.get("error"):
        return SttResponse(
            transcript="",
            intent=VoiceIntent(type="unknown", slots={}, confidence=0),
            language=language,
        )

    # Classify intent
    intent_svc = IntentService()
    intent = intent_svc.classify(stt_result["transcript"], language)

    return SttResponse(
        transcript=stt_result["transcript"],
        intent=VoiceIntent(**intent),
        language=language,
    )


@router.post("/tts")
async def text_to_speech(
    body: TtsRequest,
    redis: Redis = Depends(get_redis),
):
    """Convert text to speech audio via Bhashini TTS."""
    bhashini = BhashiniService(redis)
    audio = await bhashini.text_to_speech(body.text, body.language)

    if not audio:
        raise HTTPException(503, "TTS service unavailable")

    return Response(content=audio, media_type="audio/wav")
